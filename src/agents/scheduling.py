from __future__ import annotations

from typing import Any
from src.agents.base import BaseAgent
from src.domain.models import Contact, AppointmentSlot


class SchedulingAgent(BaseAgent):
    """Mock Scheduling Agent with tool signatures for create_contact and book_slot."""

    declared_tools: list[str] = ["create_contact", "book_slot"]

    def run_deterministic_flow(
        self,
        contact_data: dict[str, Any],
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
    ) -> dict[str, Any]:
        """Execute deterministic test invocation for Scheduling Agent: create contact and book appointment slot."""
        contact: Contact = self.execute_tool(
            "create_contact",
            {"contact_data": contact_data},
            target_crm=target_crm,
        )
        slot: AppointmentSlot = self.execute_tool(
            "book_slot",
            {
                "slot_id": slot_id,
                "attendee_email": attendee_email,
                "title": title,
            },
            target_crm=target_crm,
        )
        return {
            "contact": contact,
            "slot": slot,
        }
