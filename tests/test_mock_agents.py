from datetime import datetime, timezone
from typing import Any
import pytest

from src.domain.models import (
    Contact,
    ContactCreate,
    Order,
    OrderItem,
    AppointmentSlot,
    Payment,
)
from src.domain.errors import EntityNotFoundError, SlotConflictError, PaymentFailedError
from src.agents.support import SupportAgent
from src.agents.scheduling import SchedulingAgent
from src.agents.billing import BillingAgent


class FakeCrmClient:
    """Mock implementation conforming to CrmClientProtocol for testing agent flows."""

    def __init__(self):
        self.invocations: list[dict[str, Any]] = []

    def get_contact(self, contact_id: str | None = None, email: str | None = None, target_crm: str | None = None) -> Contact:
        self.invocations.append({"method": "get_contact", "contact_id": contact_id, "email": email, "target_crm": target_crm})
        if contact_id == "not_found" or email == "not_found@example.com":
            raise EntityNotFoundError(f"Contact {contact_id or email} not found", target_crm=target_crm)
        return Contact(
            id=contact_id or "cnt_email_123",
            first_name="Jane",
            last_name="Doe",
            email=email or "jane@example.com",
            company="Acme Corp",
        )

    def create_contact(self, contact_data: dict[str, Any] | ContactCreate, target_crm: str | None = None) -> Contact:
        self.invocations.append({"method": "create_contact", "data": contact_data, "target_crm": target_crm})
        if isinstance(contact_data, dict):
            return Contact(id="cnt_created_1", **contact_data)
        return Contact(id="cnt_created_1", **contact_data.model_dump())

    def check_order(self, order_id: str, target_crm: str | None = None) -> Order:
        self.invocations.append({"method": "check_order", "order_id": order_id, "target_crm": target_crm})
        return Order(
            id=order_id,
            contact_id="cnt_123",
            items=[OrderItem(name="Widget", quantity=1, unit_price=29.99)],
            total_amount=29.99,
            currency="USD",
            status="delivered",
        )

    def get_orders(self, contact_id: str, target_crm: str | None = None) -> list[Order]:
        self.invocations.append({"method": "get_orders", "contact_id": contact_id, "target_crm": target_crm})
        return [
            Order(
                id="ord_mock_1",
                contact_id=contact_id,
                items=[OrderItem(name="Widget", quantity=1, unit_price=29.99)],
                total_amount=29.99,
                currency="USD",
                status="delivered",
            )
        ]

    def book_slot(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
    ) -> AppointmentSlot:
        self.invocations.append({
            "method": "book_slot",
            "slot_id": slot_id,
            "attendee_email": attendee_email,
            "title": title,
            "target_crm": target_crm,
        })
        if slot_id == "conflict_slot":
            raise SlotConflictError("Slot already booked", target_crm=target_crm)
        return AppointmentSlot(
            id=slot_id,
            start_time=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc),
            title=title or "Meeting",
            attendee_email=attendee_email,
            status="booked",
        )

    def take_payment(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
    ) -> Payment:
        self.invocations.append({
            "method": "take_payment",
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "target_crm": target_crm,
        })
        if amount <= 0:
            raise PaymentFailedError("Invalid payment amount", target_crm=target_crm)
        return Payment(
            id="pay_001",
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            status="completed",
            transaction_timestamp=datetime.now(timezone.utc),
        )

    def dispatch_tool_call(self, name: str, arguments: dict[str, Any], target_crm: str | None = None) -> Any:
        method = getattr(self, name)
        kwargs = dict(arguments)
        if "target_crm" not in kwargs:
            kwargs["target_crm"] = target_crm
        return method(**kwargs)


def test_support_agent_tool_signatures():
    client = FakeCrmClient()
    agent = SupportAgent(client=client, target_crm="crm_1")
    tools = agent.get_tools()
    tool_names = [t["function"]["name"] for t in tools]

    assert "get_contact" in tool_names
    assert "check_order" in tool_names
    assert "create_contact" not in tool_names
    assert "take_payment" not in tool_names


def test_support_agent_deterministic_flow():
    client = FakeCrmClient()
    agent = SupportAgent(client=client, target_crm="crm_1")
    result = agent.run_deterministic_flow(contact_id="cnt_123", order_id="ord_456")

    assert isinstance(result["contact"], Contact)
    assert result["contact"].id == "cnt_123"
    assert isinstance(result["order"], Order)
    assert result["order"].id == "ord_456"

    # Verify calls made to client with target CRM
    invoked_methods = [inv["method"] for inv in client.invocations]
    assert invoked_methods == ["get_contact", "check_order"]
    assert client.invocations[0]["target_crm"] == "crm_1"
    assert client.invocations[1]["target_crm"] == "crm_1"


def test_support_agent_execute_tool():
    client = FakeCrmClient()
    agent = SupportAgent(client=client, target_crm="crm_2")

    contact = agent.execute_tool("get_contact", {"contact_id": "cnt_abc"})
    assert isinstance(contact, Contact)
    assert contact.id == "cnt_abc"

    # Unsupported tool raises ValueError
    with pytest.raises(ValueError, match="not supported by SupportAgent"):
        agent.execute_tool("take_payment", {"order_id": "ord_1", "amount": 50.0})


def test_scheduling_agent_tool_signatures():
    client = FakeCrmClient()
    agent = SchedulingAgent(client=client, target_crm="crm_2")
    tools = agent.get_tools()
    tool_names = [t["function"]["name"] for t in tools]

    assert "create_contact" in tool_names
    assert "book_slot" in tool_names
    assert "check_order" not in tool_names
    assert "take_payment" not in tool_names


def test_scheduling_agent_deterministic_flow():
    client = FakeCrmClient()
    agent = SchedulingAgent(client=client, target_crm="crm_2")
    contact_data = {
        "first_name": "Bob",
        "last_name": "Marley",
        "email": "bob@marley.com",
        "company": "Tuff Gong",
    }
    result = agent.run_deterministic_flow(
        contact_data=contact_data,
        slot_id="slot_789",
        attendee_email="bob@marley.com",
        title="Consultation",
    )

    assert isinstance(result["contact"], Contact)
    assert result["contact"].first_name == "Bob"
    assert isinstance(result["slot"], AppointmentSlot)
    assert result["slot"].id == "slot_789"
    assert result["slot"].status == "booked"

    invoked_methods = [inv["method"] for inv in client.invocations]
    assert invoked_methods == ["create_contact", "book_slot"]


def test_scheduling_agent_execute_tool():
    client = FakeCrmClient()
    agent = SchedulingAgent(client=client, target_crm="crm_2")

    slot = agent.execute_tool("book_slot", {"slot_id": "slot_555", "attendee_email": "test@test.com"})
    assert isinstance(slot, AppointmentSlot)
    assert slot.id == "slot_555"

    with pytest.raises(ValueError, match="not supported by SchedulingAgent"):
        agent.execute_tool("get_contact", {"contact_id": "cnt_1"})


def test_billing_agent_tool_signatures():
    client = FakeCrmClient()
    agent = BillingAgent(client=client, target_crm="crm_3")
    tools = agent.get_tools()
    tool_names = [t["function"]["name"] for t in tools]

    assert "get_contact" in tool_names
    assert "check_order" in tool_names
    assert "take_payment" in tool_names
    assert "book_slot" not in tool_names


def test_billing_agent_deterministic_flow():
    client = FakeCrmClient()
    agent = BillingAgent(client=client, target_crm="crm_3")
    result = agent.run_deterministic_flow(
        contact_id="cnt_123",
        order_id="ord_999",
        amount=29.99,
        currency="USD",
        payment_method="credit_card",
    )

    assert isinstance(result["contact"], Contact)
    assert isinstance(result["order"], Order)
    assert isinstance(result["payment"], Payment)
    assert result["payment"].amount == 29.99
    assert result["payment"].status == "completed"

    invoked_methods = [inv["method"] for inv in client.invocations]
    assert invoked_methods == ["get_contact", "check_order", "take_payment"]


def test_billing_agent_execute_tool():
    client = FakeCrmClient()
    agent = BillingAgent(client=client, target_crm="crm_3")

    payment = agent.execute_tool("take_payment", {"order_id": "ord_100", "amount": 100.0})
    assert isinstance(payment, Payment)
    assert payment.order_id == "ord_100"

    with pytest.raises(ValueError, match="not supported by BillingAgent"):
        agent.execute_tool("book_slot", {"slot_id": "slot_1", "attendee_email": "a@b.com"})


def test_scheduling_agent_slot_conflict_error():
    client = FakeCrmClient()
    agent = SchedulingAgent(client=client, target_crm="crm_2")
    contact_data = {
        "first_name": "Bob",
        "last_name": "Marley",
        "email": "bob@marley.com",
    }
    with pytest.raises(SlotConflictError):
        agent.run_deterministic_flow(
            contact_data=contact_data,
            slot_id="conflict_slot",
            attendee_email="bob@marley.com",
        )


def test_billing_agent_payment_failed_error():
    client = FakeCrmClient()
    agent = BillingAgent(client=client, target_crm="crm_3")
    with pytest.raises(PaymentFailedError):
        agent.run_deterministic_flow(
            contact_id="cnt_123",
            order_id="ord_999",
            amount=-10.0,
        )


def test_target_crm_override_in_flow():
    client = FakeCrmClient()
    agent = SupportAgent(client=client, target_crm="crm_1")
    agent.run_deterministic_flow(
        contact_id="cnt_1",
        order_id="ord_1",
        target_crm="crm_3",
    )
    assert client.invocations[0]["target_crm"] == "crm_3"
    assert client.invocations[1]["target_crm"] == "crm_3"


def test_agent_error_propagation():
    client = FakeCrmClient()
    agent = SupportAgent(client=client, target_crm="crm_1")

    with pytest.raises(EntityNotFoundError):
        agent.run_deterministic_flow(contact_id="not_found", order_id="ord_1")
