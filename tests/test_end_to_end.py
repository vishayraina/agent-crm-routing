from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pytest

from src.agents.billing import BillingAgent
from src.agents.scheduling import SchedulingAgent
from src.agents.support import SupportAgent
from src.client import CrmClient
from src.domain.errors import (
    EntityNotFoundError,
    PaymentFailedError,
    SlotConflictError,
    ValidationError,
)
from src.domain.models import AppointmentSlot, Contact, ContactCreate, Order, Payment
from src.mock_crms.data import reset_mock_data
from src.routing.app import routing_app


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Ensure in-memory mock data is clean before and after every test."""
    reset_mock_data()
    yield
    reset_mock_data()


@pytest.fixture
def client() -> CrmClient:
    """Singular Client SDK wired into the Central Routing Layer."""
    return CrmClient(app=routing_app)


# ============================================================================
# 1. SupportAgent End-to-End Tests Across CRM 1, CRM 2, and CRM 3
# ============================================================================


@pytest.mark.parametrize(
    "crm_target,contact_id,expected_name,expected_company,order_id,expected_amount,expected_status",
    [
        ("crm_1", "cont_101", "Alice Smith", "Acme Corp", "ord_101", 199.99, "shipped"),
        ("crm_2", "cnt_201", "Bob Johnson", "Beta Industries", "ord_201", 450.0, "processing"),
        ("crm_3", "rec_301", "Carol Williams", "Gamma Dynamics", "rec_ord_301", 320.5, "delivered"),
    ],
)
def test_support_agent_e2e_queries(
    client: CrmClient,
    crm_target: str,
    contact_id: str,
    expected_name: str,
    expected_company: str,
    order_id: str,
    expected_amount: float,
    expected_status: str,
) -> None:
    """Full vertical stack test: SupportAgent tool execution through Routing Layer to CRM providers."""
    agent = SupportAgent(client=client, target_crm=crm_target)

    # 1. Tool Call: get_contact
    contact_result = agent.execute_tool("get_contact", {"contact_id": contact_id})
    assert isinstance(contact_result, Contact)
    assert contact_result.id == contact_id
    assert f"{contact_result.first_name} {contact_result.last_name}" == expected_name
    assert contact_result.company == expected_company

    # 2. Tool Call: check_order
    order_result = agent.execute_tool("check_order", {"order_id": order_id})
    assert isinstance(order_result, Order)
    assert order_result.id == order_id
    assert order_result.contact_id == contact_id
    assert order_result.total_amount == pytest.approx(expected_amount)
    assert order_result.status == expected_status
    assert len(order_result.items) > 0

    # 3. Deterministic Flow
    flow_result = agent.run_deterministic_flow(contact_id=contact_id, order_id=order_id)
    assert "contact" in flow_result and "order" in flow_result
    assert flow_result["contact"].id == contact_id
    assert flow_result["order"].id == order_id


@pytest.mark.parametrize(
    "crm_target,email,expected_id,expected_name",
    [
        ("crm_1", "alice.smith@example.com", "cont_101", "Alice"),
        ("crm_2", "bob.johnson@example.com", "cnt_201", "Bob"),
        ("crm_3", "carol.williams@example.com", "rec_301", "Carol"),
    ],
)
def test_support_agent_get_contact_by_email_e2e(
    client: CrmClient,
    crm_target: str,
    email: str,
    expected_id: str,
    expected_name: str,
) -> None:
    """SupportAgent queries contact by email across heterogeneous CRM schemas."""
    agent = SupportAgent(client=client, target_crm=crm_target)
    contact = agent.execute_tool("get_contact", {"email": email})

    assert isinstance(contact, Contact)
    assert contact.id == expected_id
    assert contact.email == email
    assert contact.first_name == expected_name


# ============================================================================
# 2. SchedulingAgent End-to-End Tests Across CRM 1, CRM 2, and CRM 3
# ============================================================================


@pytest.mark.parametrize("crm_target", ["crm_1", "crm_2", "crm_3"])
def test_scheduling_agent_e2e_operations(client: CrmClient, crm_target: str) -> None:
    """Full vertical stack test: SchedulingAgent contact creation and calendar booking."""
    agent = SchedulingAgent(client=client, target_crm=crm_target)

    contact_payload = {
        "first_name": "Diana",
        "last_name": "Prince",
        "email": f"diana.prince.{crm_target}@themyscira.io",
        "phone": "+1-555-0999",
        "company": "Amazon Enterprises",
    }

    # 1. Tool Call: create_contact
    contact = agent.execute_tool("create_contact", {"contact_data": contact_payload})
    assert isinstance(contact, Contact)
    assert contact.id is not None and len(contact.id) > 0
    assert contact.first_name == "Diana"
    assert contact.last_name == "Prince"
    assert contact.email == f"diana.prince.{crm_target}@themyscira.io"
    assert contact.company == "Amazon Enterprises"

    # 2. Tool Call: book_slot
    slot_id = f"slot_sched_{crm_target}"
    attendee = contact.email
    slot = agent.execute_tool(
        "book_slot",
        {
            "slot_id": slot_id,
            "attendee_email": attendee,
            "title": f"Discovery Sync - {crm_target}",
        },
    )
    assert isinstance(slot, AppointmentSlot)
    assert slot.id == slot_id
    assert slot.attendee_email == attendee
    assert slot.status == "confirmed"
    assert slot.title == f"Discovery Sync - {crm_target}"

    # 3. Deterministic Flow
    flow_slot_id = f"slot_flow_{crm_target}"
    flow_data = {
        "first_name": "Clark",
        "last_name": "Kent",
        "email": f"clark.{crm_target}@dailyplanet.com",
        "phone": "+1-555-0777",
        "company": "Daily Planet",
    }
    flow_result = agent.run_deterministic_flow(
        contact_data=flow_data,
        slot_id=flow_slot_id,
        attendee_email=flow_data["email"],
        title="Editorial Interview",
    )
    assert isinstance(flow_result["contact"], Contact)
    assert isinstance(flow_result["slot"], AppointmentSlot)
    assert flow_result["contact"].first_name == "Clark"
    assert flow_result["slot"].id == flow_slot_id
    assert flow_result["slot"].status == "confirmed"


# ============================================================================
# 3. BillingAgent End-to-End Tests Across CRM 1, CRM 2, and CRM 3
# ============================================================================


@pytest.mark.parametrize(
    "crm_target,contact_id,order_id,amount,payment_method",
    [
        ("crm_1", "cont_101", "ord_101", 199.99, "card_visa"),
        ("crm_2", "cnt_201", "ord_201", 450.0, "tok_mastercard"),
        ("crm_3", "rec_301", "rec_ord_301", 320.5, "corporate_ach"),
    ],
)
def test_billing_agent_e2e_operations(
    client: CrmClient,
    crm_target: str,
    contact_id: str,
    order_id: str,
    amount: float,
    payment_method: str,
) -> None:
    """Full vertical stack test: BillingAgent order retrieval and monetary charge."""
    agent = BillingAgent(client=client, target_crm=crm_target)

    # 1. Tool Call: check_order
    order = agent.execute_tool("check_order", {"order_id": order_id})
    assert isinstance(order, Order)
    assert order.id == order_id
    assert order.contact_id == contact_id
    assert order.total_amount == pytest.approx(amount)

    # 2. Tool Call: take_payment
    payment = agent.execute_tool(
        "take_payment",
        {
            "order_id": order_id,
            "amount": amount,
            "currency": "USD",
            "payment_method": payment_method,
        },
    )
    assert isinstance(payment, Payment)
    assert payment.id is not None
    assert payment.order_id == order_id
    assert payment.amount == pytest.approx(amount)
    assert payment.currency == "USD"
    assert payment.status == "completed"
    assert payment.payment_method == payment_method

    # 3. Deterministic Flow
    flow_result = agent.run_deterministic_flow(
        contact_id=contact_id,
        order_id=order_id,
        amount=amount,
        currency="USD",
        payment_method=payment_method,
    )
    assert isinstance(flow_result["contact"], Contact)
    assert isinstance(flow_result["order"], Order)
    assert isinstance(flow_result["payment"], Payment)
    assert flow_result["payment"].status == "completed"


# ============================================================================
# 4. Negative Error Scenarios Across All CRMs
#    (EntityNotFoundError, SlotConflictError, PaymentFailedError)
# ============================================================================


@pytest.mark.parametrize("crm_target", ["crm_1", "crm_2", "crm_3"])
def test_e2e_negative_contact_not_found(client: CrmClient, crm_target: str) -> None:
    """Verify non-existent contact errors are normalized into EntityNotFoundError in SDK & Tool Calls."""
    missing_id = f"missing_contact_{crm_target}"

    # Direct client call raises typed EntityNotFoundError
    with pytest.raises(EntityNotFoundError) as exc_info:
        client.get_contact(missing_id, target_crm=crm_target)
    err = exc_info.value
    assert err.error_type == "EntityNotFoundError"
    assert err.target_crm == crm_target

    # Namespace helper raises typed EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        client.contacts.get(missing_id, target_crm=crm_target)

    # dispatch_tool_call returns structured canonical error dict
    tool_resp = client.dispatch_tool_call(
        "get_contact",
        {"contact_id": missing_id},
        target_crm=crm_target,
    )
    assert isinstance(tool_resp, dict)
    assert tool_resp.get("error") is True
    assert tool_resp.get("error_type") == "EntityNotFoundError"
    assert tool_resp.get("target_crm") == crm_target
    assert any(phrase in tool_resp.get("message", "").lower() for phrase in ("not found", "does not exist", "not located"))

    # Agent execution handles error seamlessly without unhandled exception
    support_agent = SupportAgent(client=client, target_crm=crm_target)
    agent_resp = support_agent.execute_tool("get_contact", {"contact_id": missing_id})
    assert agent_resp["error"] is True
    assert agent_resp["error_type"] == "EntityNotFoundError"


@pytest.mark.parametrize("crm_target", ["crm_1", "crm_2", "crm_3"])
def test_e2e_negative_order_not_found(client: CrmClient, crm_target: str) -> None:
    """Verify non-existent order errors are normalized into EntityNotFoundError in SDK & Tool Calls."""
    missing_id = f"missing_order_{crm_target}"

    # Direct client call
    with pytest.raises(EntityNotFoundError) as exc_info:
        client.check_order(missing_id, target_crm=crm_target)
    err = exc_info.value
    assert err.error_type == "EntityNotFoundError"
    assert err.target_crm == crm_target

    # Namespace helper
    with pytest.raises(EntityNotFoundError):
        client.orders.check(missing_id, target_crm=crm_target)

    # dispatch_tool_call
    tool_resp = client.dispatch_tool_call(
        "check_order",
        {"order_id": missing_id},
        target_crm=crm_target,
    )
    assert tool_resp.get("error") is True
    assert tool_resp.get("error_type") == "EntityNotFoundError"
    assert tool_resp.get("target_crm") == crm_target

    # Agent execution
    billing_agent = BillingAgent(client=client, target_crm=crm_target)
    agent_resp = billing_agent.execute_tool("check_order", {"order_id": missing_id})
    assert agent_resp["error"] is True
    assert agent_resp["error_type"] == "EntityNotFoundError"


@pytest.mark.parametrize(
    "crm_target,conflict_slot_id",
    [
        ("crm_1", "slot_conflict"),
        ("crm_2", "slot_conflict"),
        ("crm_3", "rec_slot_conflict"),
    ],
)
def test_e2e_negative_slot_conflict(
    client: CrmClient,
    crm_target: str,
    conflict_slot_id: str,
) -> None:
    """Verify booking collisions are normalized into SlotConflictError (HTTP 409)."""
    # Direct client call
    with pytest.raises(SlotConflictError) as exc_info:
        client.book_slot(
            slot_id=conflict_slot_id,
            attendee_email="conflict.candidate@example.com",
            target_crm=crm_target,
        )
    err = exc_info.value
    assert err.error_type == "SlotConflictError"
    assert err.target_crm == crm_target

    # Namespace helper
    with pytest.raises(SlotConflictError):
        client.appointments.book(
            slot_id=conflict_slot_id,
            attendee_email="conflict.candidate@example.com",
            target_crm=crm_target,
        )

    # dispatch_tool_call
    tool_resp = client.dispatch_tool_call(
        "book_slot",
        {
            "slot_id": conflict_slot_id,
            "attendee_email": "conflict.candidate@example.com",
            "title": "Colliding Meeting",
        },
        target_crm=crm_target,
    )
    assert tool_resp.get("error") is True
    assert tool_resp.get("error_type") == "SlotConflictError"
    assert tool_resp.get("target_crm") == crm_target
    assert "conflict" in tool_resp.get("message", "").lower() or "already reserved" in tool_resp.get("message", "").lower()

    # Agent execution
    sched_agent = SchedulingAgent(client=client, target_crm=crm_target)
    agent_resp = sched_agent.execute_tool(
        "book_slot",
        {
            "slot_id": conflict_slot_id,
            "attendee_email": "conflict.candidate@example.com",
        },
    )
    assert agent_resp["error"] is True
    assert agent_resp["error_type"] == "SlotConflictError"


@pytest.mark.parametrize(
    "crm_target,declined_method",
    [
        ("crm_1", "card_declined"),
        ("crm_2", "tok_declined"),
        ("crm_3", "declined_ach"),
    ],
)
def test_e2e_negative_payment_declined(
    client: CrmClient,
    crm_target: str,
    declined_method: str,
) -> None:
    """Verify payment declines are normalized into PaymentFailedError (HTTP 402)."""
    # Direct client call
    with pytest.raises(PaymentFailedError) as exc_info:
        client.take_payment(
            order_id="ord_e2e_test",
            amount=99.00,
            payment_method=declined_method,
            target_crm=crm_target,
        )
    err = exc_info.value
    assert err.error_type == "PaymentFailedError"
    assert err.target_crm == crm_target

    # Namespace helper
    with pytest.raises(PaymentFailedError):
        client.payments.take(
            order_id="ord_e2e_test",
            amount=99.00,
            payment_method=declined_method,
            target_crm=crm_target,
        )

    # dispatch_tool_call
    tool_resp = client.dispatch_tool_call(
        "take_payment",
        {
            "order_id": "ord_e2e_test",
            "amount": 99.00,
            "payment_method": declined_method,
        },
        target_crm=crm_target,
    )
    assert tool_resp.get("error") is True
    assert tool_resp.get("error_type") == "PaymentFailedError"
    assert tool_resp.get("target_crm") == crm_target
    assert "declined" in tool_resp.get("message", "").lower()

    # Agent execution
    billing_agent = BillingAgent(client=client, target_crm=crm_target)
    agent_resp = billing_agent.execute_tool(
        "take_payment",
        {
            "order_id": "ord_e2e_test",
            "amount": 99.00,
            "payment_method": declined_method,
        },
    )
    assert agent_resp["error"] is True
    assert agent_resp["error_type"] == "PaymentFailedError"


# ============================================================================
# 5. Full End-to-End Multi-Agent Multi-CRM Collaboration Lifecycle
# ============================================================================


def test_e2e_full_lifecycle_multistep_flow(client: CrmClient) -> None:
    """
    Test realistic cross-CRM multi-agent workflow:
    1. SchedulingAgent captures lead and schedules slot in CRM 2.
    2. SupportAgent verifies contact record and checks order in CRM 1.
    3. BillingAgent checks customer order and charges payment in CRM 3.
    4. SchedulingAgent encounters a booking collision on the scheduled slot.
    5. BillingAgent attempts a charge with a declined method and recovers with a valid method.
    """
    sched_crm2 = SchedulingAgent(client=client, target_crm="crm_2")
    support_crm1 = SupportAgent(client=client, target_crm="crm_1")
    billing_crm3 = BillingAgent(client=client, target_crm="crm_3")

    # Step 1: SchedulingAgent in CRM 2
    new_contact = sched_crm2.execute_tool(
        "create_contact",
        {
            "contact_data": {
                "first_name": "Bruce",
                "last_name": "Wayne",
                "email": "bruce.wayne@waynecorp.com",
                "phone": "+1-555-0987",
                "company": "Wayne Enterprises",
            }
        },
    )
    assert isinstance(new_contact, Contact)
    assert new_contact.first_name == "Bruce"
    assert new_contact.company == "Wayne Enterprises"

    booked_slot = sched_crm2.execute_tool(
        "book_slot",
        {
            "slot_id": "slot_wayne_001",
            "attendee_email": new_contact.email,
            "title": "Executive Product Demo",
        },
    )
    assert isinstance(booked_slot, AppointmentSlot)
    assert booked_slot.status == "confirmed"

    # Step 2: SupportAgent in CRM 1
    c1_contact = support_crm1.execute_tool("get_contact", {"contact_id": "cont_101"})
    assert isinstance(c1_contact, Contact)
    assert c1_contact.first_name == "Alice"

    c1_order = support_crm1.execute_tool("check_order", {"order_id": "ord_101"})
    assert isinstance(c1_order, Order)
    assert c1_order.status == "shipped"

    # Step 3: BillingAgent in CRM 3
    c3_order = billing_crm3.execute_tool("check_order", {"order_id": "rec_ord_301"})
    assert isinstance(c3_order, Order)
    assert c3_order.total_amount == pytest.approx(320.50)

    c3_payment = billing_crm3.execute_tool(
        "take_payment",
        {
            "order_id": "rec_ord_301",
            "amount": 320.50,
            "currency": "USD",
            "payment_method": "corporate_ach",
        },
    )
    assert isinstance(c3_payment, Payment)
    assert c3_payment.status == "completed"

    # Step 4: Collision detection on already booked slot in CRM 2
    collision_attempt = sched_crm2.execute_tool(
        "book_slot",
        {
            "slot_id": "slot_wayne_001",
            "attendee_email": "impostor@waynecorp.com",
            "title": "Conflicting Demo",
        },
    )
    assert collision_attempt["error"] is True
    assert collision_attempt["error_type"] == "SlotConflictError"
    assert collision_attempt["target_crm"] == "crm_2"

    # Step 5: Billing decline followed by recovery with valid method
    decline_attempt = billing_crm3.execute_tool(
        "take_payment",
        {
            "order_id": "rec_ord_301",
            "amount": 50.00,
            "payment_method": "declined_ach",
        },
    )
    assert decline_attempt["error"] is True
    assert decline_attempt["error_type"] == "PaymentFailedError"

    recovered_payment = billing_crm3.execute_tool(
        "take_payment",
        {
            "order_id": "rec_ord_301",
            "amount": 50.00,
            "payment_method": "corporate_ach",
        },
    )
    assert isinstance(recovered_payment, Payment)
    assert recovered_payment.status == "completed"
