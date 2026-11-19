from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from src.domain.models import Contact, ContactCreate, Order, AppointmentSlot, Payment


@runtime_checkable
class CrmClientProtocol(Protocol):
    """Protocol defining the singular Client SDK contract required by Mock Agents."""

    def get_contact(self, contact_id: str, target_crm: str | None = None) -> Contact:
        """Fetch contact details by contact ID."""
        ...

    def create_contact(self, contact_data: dict[str, Any] | ContactCreate, target_crm: str | None = None) -> Contact:
        """Create a new contact in the target CRM."""
        ...

    def check_order(self, order_id: str, target_crm: str | None = None) -> Order:
        """Fetch order details and shipment status by order ID."""
        ...

    def book_slot(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
    ) -> AppointmentSlot:
        """Book an appointment slot on a CRM calendar."""
        ...

    def take_payment(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
    ) -> Payment:
        """Charge and record a payment against an order."""
        ...

    def dispatch_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
    ) -> Any:
        """Execute a tool invocation by name and arguments."""
        ...
