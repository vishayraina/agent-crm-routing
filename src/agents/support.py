from __future__ import annotations

from typing import Any
from src.agents.base import BaseAgent
from src.domain.models import Contact, Order


class SupportAgent(BaseAgent):
    """Mock Support Agent with tool signatures for get_contact and check_order."""

    declared_tools: list[str] = ["get_contact", "check_order"]

    def run_deterministic_flow(
        self,
        contact_id: str,
        order_id: str,
        target_crm: str | None = None,
    ) -> dict[str, Any]:
        """Execute deterministic test invocation for Support Agent: fetch contact and check order."""
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
        return {
            "contact": contact,
            "order": order,
        }
