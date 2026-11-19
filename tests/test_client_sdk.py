from datetime import datetime, timezone
from typing import Any
import pytest
import httpx
from fastapi.testclient import TestClient

from src.domain.contracts import CrmClientProtocol
from src.domain.models import AppointmentSlot, Contact, ContactCreate, Order, Payment
from src.domain.errors import (
    CanonicalError,
    CanonicalException,
    EntityNotFoundError,
    PaymentFailedError,
    ProviderUnavailableError,
    SlotConflictError,
    ValidationError,
)
from src.domain.tools import ALL_TOOLS
from src.routing.app import routing_app, create_routing_app
from src.mock_crms.data import reset_mock_data
from src.agents.support import SupportAgent
from src.agents.scheduling import SchedulingAgent
from src.agents.billing import BillingAgent

from src.client import (
    CrmClient,
    ContactsNamespace,
    OrdersNamespace,
    AppointmentsNamespace,
    PaymentsNamespace,
)


@pytest.fixture(autouse=True)
def clean_data():
    reset_mock_data()
    yield


@pytest.fixture
def test_client():
    return CrmClient(app=routing_app, crm_target="crm_1")


# ============================================================================
# 1. Initialization and Protocol Conformance
# ============================================================================


def test_client_protocol_conformance(test_client):
    assert isinstance(test_client, CrmClientProtocol)


def test_client_initialization_options():
    # Default init
    c1 = CrmClient()
    assert c1.base_url == "http://localhost:8000"
    assert c1.crm_target == "crm_1"
    c1.close()

    # Custom target and base_url
    c2 = CrmClient(base_url="http://custom-api:9000", crm_target="crm_2")
    assert c2.base_url == "http://custom-api:9000"
    assert c2.crm_target == "crm_2"
    c2.close()

    # With app
    c3 = CrmClient(app=routing_app, crm_target="crm_3")
    assert c3.crm_target == "crm_3"
    assert c3._client is not None
    c3.close()

    # With existing TestClient
    raw_tc = TestClient(routing_app)
    c4 = CrmClient(client=raw_tc, crm_target="crm_1")
    assert c4._client is raw_tc
    c4.close()

    # With httpx.Client configured with ASGITransport
    asgi_client = httpx.Client(
        transport=httpx.ASGITransport(app=routing_app),
        base_url="http://testserver",
    )
    c5 = CrmClient(client=asgi_client, crm_target="crm_2")
    assert c5.crm_target == "crm_2"
    res = c5.get_contact("cnt_201")
    assert res.id == "cnt_201"
    c5.close()


def test_client_context_manager():
    with CrmClient(app=routing_app, crm_target="crm_1") as client:
        assert isinstance(client, CrmClient)
        contact = client.get_contact("cont_101")
        assert contact.id == "cont_101"


# ============================================================================
# 2. Tool Declarations Export
# ============================================================================


def test_get_tools_returns_all_tools(test_client):
    tools = test_client.get_tools()
    assert isinstance(tools, list)
    assert len(tools) == len(ALL_TOOLS)
    tool_names = [t["function"]["name"] for t in tools]
    assert set(tool_names) == set(ALL_TOOLS.keys())
    for t in tools:
        assert t["type"] == "function"
        assert "parameters" in t["function"]
        assert "description" in t["function"]


def test_get_tools_with_filter(test_client):
    filtered = test_client.get_tools(["get_contact", "check_order"])
    assert len(filtered) == 2
    names = [t["function"]["name"] for t in filtered]
    assert names == ["get_contact", "check_order"]


def test_get_tool_names(test_client):
    names = test_client.get_tool_names()
    assert set(names) == {"get_contact", "create_contact", "check_order", "book_slot", "take_payment"}


# ============================================================================
# 3. Direct Typed Methods
# ============================================================================


@pytest.mark.parametrize("crm_target,contact_id,expected_first_name", [
    ("crm_1", "cont_101", "Alice"),
    ("crm_2", "cnt_201", "Bob"),
    ("crm_3", "rec_301", "Carol"),
])
def test_get_contact_success(test_client, crm_target, contact_id, expected_first_name):
    contact = test_client.get_contact(contact_id=contact_id, target_crm=crm_target)
    assert isinstance(contact, Contact)
    assert contact.id == contact_id
    assert contact.first_name == expected_first_name


def test_get_contact_by_email(test_client):
    contact = test_client.get_contact(email="alice.smith@example.com", target_crm="crm_1")
    assert isinstance(contact, Contact)
    assert contact.id == "cont_101"
    assert contact.first_name == "Alice"


def test_get_contact_not_found_raises_entity_not_found(test_client):
    with pytest.raises(EntityNotFoundError) as exc_info:
        test_client.get_contact("nonexistent_id", target_crm="crm_1")
    assert exc_info.value.target_crm == "crm_1"
    assert "nonexistent_id" in exc_info.value.message


@pytest.mark.parametrize("crm_target", ["crm_1", "crm_2", "crm_3"])
def test_create_contact_dict_and_model(test_client, crm_target):
    # From dictionary
    data_dict = {
        "first_name": "Dev",
        "last_name": "Tester",
        "email": f"dev.tester@{crm_target}.com",
        "phone": "+1-555-0100",
        "company": "Test LLC",
    }
    contact1 = test_client.create_contact(data_dict, target_crm=crm_target)
    assert isinstance(contact1, Contact)
    assert contact1.first_name == "Dev"
    assert contact1.email == f"dev.tester@{crm_target}.com"
    assert contact1.id is not None

    # From ContactCreate model
    model = ContactCreate(
        first_name="Model",
        last_name="Tester",
        email=f"model.tester@{crm_target}.com",
    )
    contact2 = test_client.create_contact(model, target_crm=crm_target)
    assert isinstance(contact2, Contact)
    assert contact2.first_name == "Model"
    assert contact2.email == f"model.tester@{crm_target}.com"


@pytest.mark.parametrize("crm_target,order_id,expected_total", [
    ("crm_1", "ord_101", 199.99),
    ("crm_2", "ord_201", 450.00),
    ("crm_3", "rec_ord_301", 320.50),
])
def test_check_order_success(test_client, crm_target, order_id, expected_total):
    order = test_client.check_order(order_id, target_crm=crm_target)
    assert isinstance(order, Order)
    assert order.id == order_id
    assert order.total_amount == expected_total
    assert len(order.items) > 0


def test_check_order_not_found(test_client):
    with pytest.raises(EntityNotFoundError) as exc_info:
        test_client.check_order("ord_nonexistent", target_crm="crm_2")
    assert exc_info.value.target_crm == "crm_2"


@pytest.mark.parametrize("crm_target,slot_id", [
    ("crm_1", "slot_sdk_1"),
    ("crm_2", "slot_sdk_2"),
    ("crm_3", "rec_slot_sdk_3"),
])
def test_book_slot_success(test_client, crm_target, slot_id):
    slot = test_client.book_slot(
        slot_id=slot_id,
        attendee_email=f"user@{crm_target}.com",
        title="Sync Meeting",
        target_crm=crm_target,
    )
    assert isinstance(slot, AppointmentSlot)
    assert slot.id == slot_id
    assert slot.attendee_email == f"user@{crm_target}.com"


def test_book_slot_conflict_raises_slot_conflict(test_client):
    with pytest.raises(SlotConflictError) as exc_info:
        test_client.book_slot(
            slot_id="slot_conflict",
            attendee_email="conflict@example.com",
            target_crm="crm_1",
        )
    assert exc_info.value.target_crm == "crm_1"


@pytest.mark.parametrize("crm_target,order_id,amount,method", [
    ("crm_1", "ord_101", 199.99, "card_visa"),
    ("crm_2", "ord_201", 450.0, "tok_mastercard"),
    ("crm_3", "rec_ord_301", 320.50, "corporate_ach"),
])
def test_take_payment_success(test_client, crm_target, order_id, amount, method):
    payment = test_client.take_payment(
        order_id=order_id,
        amount=amount,
        currency="USD",
        payment_method=method,
        target_crm=crm_target,
    )
    assert isinstance(payment, Payment)
    assert payment.order_id == order_id
    assert payment.amount == amount
    assert payment.status in ("completed", "settled")


def test_take_payment_failed_raises_payment_failed(test_client):
    with pytest.raises(PaymentFailedError) as exc_info:
        test_client.take_payment(
            order_id="ord_declined",
            amount=50.0,
            payment_method="declined_card",
            target_crm="crm_1",
        )
    assert exc_info.value.target_crm == "crm_1"


# ============================================================================
# 4. Namespace Helpers
# ============================================================================


def test_namespace_helpers(test_client):
    assert isinstance(test_client.contacts, ContactsNamespace)
    assert isinstance(test_client.orders, OrdersNamespace)
    assert isinstance(test_client.appointments, AppointmentsNamespace)
    assert isinstance(test_client.payments, PaymentsNamespace)

    # contacts.get and contacts.create
    c = test_client.contacts.get("cont_101", target_crm="crm_1")
    assert c.id == "cont_101"
    new_c = test_client.contacts.create({"first_name": "Ns", "last_name": "Test", "email": "ns@crm1.com"}, target_crm="crm_1")
    assert new_c.first_name == "Ns"

    # orders.check and orders.get
    o1 = test_client.orders.check("ord_101", target_crm="crm_1")
    o2 = test_client.orders.get("ord_101", target_crm="crm_1")
    assert o1.id == o2.id == "ord_101"

    # appointments.book
    s = test_client.appointments.book("slot_ns_1", attendee_email="ns@example.com", target_crm="crm_1")
    assert s.id == "slot_ns_1"

    # payments.take and payments.charge
    p1 = test_client.payments.take("ord_101", amount=10.0, payment_method="card_visa", target_crm="crm_1")
    p2 = test_client.payments.charge("ord_101", amount=20.0, payment_method="card_visa", target_crm="crm_1")
    assert p1.amount == 10.0
    assert p2.amount == 20.0


# ============================================================================
# 5. dispatch_tool_call
# ============================================================================


def test_dispatch_tool_call_unknown_tool(test_client):
    result = test_client.dispatch_tool_call("nonexistent_tool", {"foo": "bar"}, target_crm="crm_1")
    assert isinstance(result, dict)
    assert result.get("error") is True
    assert result.get("error_type") == "ValidationError"
    assert "Unknown tool" in result.get("message", "")


def test_dispatch_tool_call_get_contact_success(test_client):
    result = test_client.dispatch_tool_call("get_contact", {"contact_id": "cont_101"}, target_crm="crm_1")
    assert isinstance(result, Contact)
    assert result.id == "cont_101"
    assert result.first_name == "Alice"


def test_dispatch_tool_call_get_contact_return_dict(test_client):
    result = test_client.dispatch_tool_call(
        "get_contact",
        {"contact_id": "cont_101"},
        target_crm="crm_1",
        return_dict=True,
    )
    assert isinstance(result, dict)
    assert result["id"] == "cont_101"
    assert result["first_name"] == "Alice"


def test_dispatch_tool_call_get_contact_not_found(test_client):
    result = test_client.dispatch_tool_call("get_contact", {"contact_id": "missing_cont"}, target_crm="crm_1")
    assert isinstance(result, dict)
    assert result.get("error") is True
    assert result.get("error_type") == "EntityNotFoundError"
    assert result.get("target_crm") == "crm_1"
    assert "missing_cont" in result.get("message", "")


def test_dispatch_tool_call_create_contact_success(test_client):
    # Flat arguments
    flat_args = {
        "first_name": "Dispatch",
        "last_name": "Test",
        "email": "dispatch@example.com",
    }
    res1 = test_client.dispatch_tool_call("create_contact", flat_args, target_crm="crm_1")
    assert isinstance(res1, Contact)
    assert res1.first_name == "Dispatch"

    # Nested contact_data argument
    nested_args = {
        "contact_data": {
            "first_name": "Nested",
            "last_name": "Test",
            "email": "nested@example.com",
        }
    }
    res2 = test_client.dispatch_tool_call("create_contact", nested_args, target_crm="crm_1")
    assert isinstance(res2, Contact)
    assert res2.first_name == "Nested"


def test_dispatch_tool_call_check_order_success_and_error(test_client):
    # Success
    res = test_client.dispatch_tool_call("check_order", {"order_id": "ord_101"}, target_crm="crm_1")
    assert isinstance(res, Order)
    assert res.id == "ord_101"

    # Not found
    err_res = test_client.dispatch_tool_call("check_order", {"order_id": "missing_ord"}, target_crm="crm_2")
    assert isinstance(err_res, dict)
    assert err_res.get("error") is True
    assert err_res.get("error_type") == "EntityNotFoundError"
    assert err_res.get("target_crm") == "crm_2"


def test_dispatch_tool_call_book_slot_success_and_conflict(test_client):
    # Success
    res = test_client.dispatch_tool_call(
        "book_slot",
        {"slot_id": "slot_disp_1", "attendee_email": "disp@crm1.com", "title": "Chat"},
        target_crm="crm_1",
    )
    assert isinstance(res, AppointmentSlot)
    assert res.id == "slot_disp_1"

    # Conflict
    err_res = test_client.dispatch_tool_call(
        "book_slot",
        {"slot_id": "slot_conflict", "attendee_email": "disp@crm1.com"},
        target_crm="crm_1",
    )
    assert isinstance(err_res, dict)
    assert err_res.get("error") is True
    assert err_res.get("error_type") == "SlotConflictError"


def test_dispatch_tool_call_take_payment_success_and_fail(test_client):
    # Success
    res = test_client.dispatch_tool_call(
        "take_payment",
        {"order_id": "ord_101", "amount": 50.0, "currency": "USD", "payment_method": "card_visa"},
        target_crm="crm_1",
    )
    assert isinstance(res, Payment)
    assert res.order_id == "ord_101"

    # Failure
    err_res = test_client.dispatch_tool_call(
        "take_payment",
        {"order_id": "ord_declined", "amount": 50.0, "payment_method": "declined_card"},
        target_crm="crm_1",
    )
    assert isinstance(err_res, dict)
    assert err_res.get("error") is True
    assert err_res.get("error_type") == "PaymentFailedError"


# ============================================================================
# 6. Mock Agents Integration with CrmClient
# ============================================================================


@pytest.mark.parametrize("crm_target,contact_id,order_id", [
    ("crm_1", "cont_101", "ord_101"),
    ("crm_2", "cnt_201", "ord_201"),
    ("crm_3", "rec_301", "rec_ord_301"),
])
def test_support_agent_with_crm_client(test_client, crm_target, contact_id, order_id):
    agent = SupportAgent(client=test_client, target_crm=crm_target)
    result = agent.run_deterministic_flow(contact_id=contact_id, order_id=order_id)
    assert isinstance(result["contact"], Contact)
    assert result["contact"].id == contact_id
    assert isinstance(result["order"], Order)
    assert result["order"].id == order_id


@pytest.mark.parametrize("crm_target,slot_id", [
    ("crm_1", "slot_agent_1"),
    ("crm_2", "slot_agent_2"),
    ("crm_3", "rec_slot_agent_3"),
])
def test_scheduling_agent_with_crm_client(test_client, crm_target, slot_id):
    agent = SchedulingAgent(client=test_client, target_crm=crm_target)
    contact_data = {
        "first_name": "Agent",
        "last_name": "Schedule",
        "email": f"agent.schedule@{crm_target}.com",
    }
    result = agent.run_deterministic_flow(
        contact_data=contact_data,
        slot_id=slot_id,
        attendee_email=f"agent.schedule@{crm_target}.com",
        title="Consultation",
    )
    assert isinstance(result["contact"], Contact)
    assert result["contact"].first_name == "Agent"
    assert isinstance(result["slot"], AppointmentSlot)
    assert result["slot"].id == slot_id


@pytest.mark.parametrize("crm_target,contact_id,order_id,amount,method", [
    ("crm_1", "cont_101", "ord_101", 199.99, "card_visa"),
    ("crm_2", "cnt_201", "ord_201", 450.00, "tok_mastercard"),
    ("crm_3", "rec_301", "rec_ord_301", 320.50, "corporate_ach"),
])
def test_billing_agent_with_crm_client(test_client, crm_target, contact_id, order_id, amount, method):
    agent = BillingAgent(client=test_client, target_crm=crm_target)
    result = agent.run_deterministic_flow(
        contact_id=contact_id,
        order_id=order_id,
        amount=amount,
        currency="USD",
        payment_method=method,
    )
    assert isinstance(result["contact"], Contact)
    assert result["contact"].id == contact_id
    assert isinstance(result["order"], Order)
    assert result["order"].id == order_id
    assert isinstance(result["payment"], Payment)
    assert result["payment"].order_id == order_id


# ============================================================================
# 7. Error Handling & Network Resilience Edge Cases
# ============================================================================


def test_network_connection_error_raises_provider_unavailable(monkeypatch):
    client = CrmClient(base_url="http://mock-service", crm_target="crm_1")

    def mock_get(*args, **kwargs):
        raise httpx.ConnectError("Failed to connect to server")

    monkeypatch.setattr(client._client, "get", mock_get)

    with pytest.raises(ProviderUnavailableError) as exc_info:
        client.get_contact("cont_101")
    assert exc_info.value.target_crm == "crm_1"
    assert "failed to connect" in exc_info.value.message.lower()
    client.close()


def test_unknown_target_crm_error(test_client):
    with pytest.raises(ValidationError) as exc_info:
        test_client.get_contact("cont_101", target_crm="invalid_crm")
    assert "invalid_crm" in exc_info.value.message.lower() or "target" in exc_info.value.message.lower()


def test_dispatch_tool_call_missing_required_params(test_client):
    # get_contact without params
    res1 = test_client.dispatch_tool_call("get_contact", {}, target_crm="crm_1")
    assert res1.get("error") is True
    assert res1.get("error_type") == "ValidationError"

    # check_order without order_id
    res2 = test_client.dispatch_tool_call("check_order", {}, target_crm="crm_1")
    assert res2.get("error") is True
    assert res2.get("error_type") == "ValidationError"

    # book_slot without attendee_email
    res3 = test_client.dispatch_tool_call("book_slot", {"slot_id": "slot_1"}, target_crm="crm_1")
    assert res3.get("error") is True
    assert res3.get("error_type") == "ValidationError"

    # take_payment without amount
    res4 = test_client.dispatch_tool_call("take_payment", {"order_id": "ord_101"}, target_crm="crm_1")
    assert res4.get("error") is True
    assert res4.get("error_type") == "ValidationError"

    # take_payment with invalid non-numeric amount
    res5 = test_client.dispatch_tool_call("take_payment", {"order_id": "ord_101", "amount": "invalid_num"}, target_crm="crm_1")
    assert res5.get("error") is True
    assert res5.get("error_type") == "ValidationError"


def test_direct_typed_method_missing_params(test_client):
    with pytest.raises(ValidationError):
        test_client.get_contact()

    with pytest.raises(ValidationError):
        test_client.create_contact("invalid_payload_type")  # type: ignore
