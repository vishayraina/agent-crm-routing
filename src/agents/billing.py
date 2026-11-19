from __future__ import annotations

from typing import Any
from src.agents.base import BaseAgent
from src.domain.models import Contact, Order, Payment


class BillingAgent(BaseAgent):
    """Mock Billing Agent with tool signatures for get_contact, check_order, get_orders, and take_payment."""

    declared_tools: list[str] = ["get_contact", "check_order", "get_orders", "take_payment"]

    def run_deterministic_flow(
        self,
        contact_id: str,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
    ) -> dict[str, Any]:
        """Execute deterministic test invocation for Billing Agent: fetch contact, check order, and charge payment."""
        contact: Contact = self.execute_tool(
            "get_contact",
            {"contact_id": contact_id},
            target_crm=target_crm,
        )
        order: Order = self.execute_tool(
            "check_order",
            {"order_id": order_id},
            target_crm=target_crm,
        )
        payment: Payment = self.execute_tool(
            "take_payment",
            {
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
            },
            target_crm=target_crm,
        )
        return {
            "contact": contact,
            "order": order,
            "payment": payment,
        }
