#!/usr/bin/env python3
"""
Agent-to-CRM Centralized Routing Platform — Verification Demo Runner.

Demonstrates full vertical execution:
    Agent Tool Invocation -> Client SDK -> Routing Layer -> Adapters -> Mock CRMs
Validating:
    1. SupportAgent flows across CRM 1, CRM 2, CRM 3
    2. SchedulingAgent flows across CRM 1, CRM 2, CRM 3
    3. BillingAgent flows across CRM 1, CRM 2, CRM 3
    4. Canonical Error Normalization & Agent Self-Healing across all 3 CRMs
"""

from __future__ import annotations

import json
import sys
from typing import Any

from src.agents.billing import BillingAgent
from src.agents.scheduling import SchedulingAgent
from src.agents.support import SupportAgent
from src.client import CrmClient
from src.domain.errors import (
    EntityNotFoundError,
    PaymentFailedError,
    SlotConflictError,
)
from src.mock_crms.data import reset_mock_data
from src.routing.app import routing_app

# ANSI Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner() -> None:
    print(f"\n{CYAN}{BOLD}" + "=" * 80)
    print("   AGENT-TO-CRM ROUTING PLATFORM: LIVE END-TO-END DEMO RUNNER")
    print("=" * 80 + f"{RESET}\n")
    print(f"{DIM}Connecting Agents to Heterogeneous CRMs via Centralized Routing Layer:{RESET}")
    print(f"  • {BOLD}CRM 1{RESET}: Flat REST (snake_case, ISO-8601 timestamps)")
    print(f"  • {BOLD}CRM 2{RESET}: Nested RPC (camelCase, epoch ms timestamps, RPC status codes)")
    print(f"  • {BOLD}CRM 3{RESET}: Dynamic Property-Bag (dynamic 'properties' dictionary, string decimals)")
    print("-" * 80 + "\n")


def print_section(title: str) -> None:
    print(f"\n{MAGENTA}{BOLD}[STEP] {title}{RESET}")
    print(f"{MAGENTA}" + "-" * 70 + f"{RESET}")


def print_success(message: str) -> None:
    print(f"  {GREEN}✔{RESET} {message}")


def print_detail(label: str, value: Any) -> None:
    if isinstance(value, dict):
        formatted = json.dumps(value, indent=4)
        print(f"    {DIM}{label}:{RESET}\n    {formatted}")
    else:
        print(f"    {DIM}{label}:{RESET} {BOLD}{value}{RESET}")


def run_demo() -> int:
    # Reset mock CRM state
    reset_mock_data()

    # Initialize client SDK wired directly to the Central Routing Layer
    client = CrmClient(app=routing_app)

    print_banner()

    total_checks = 0

    # =========================================================================
    # Step 1: SupportAgent Across All 3 CRMs
    # =========================================================================
    print_section("1. SupportAgent Tool Invocations Across CRMs")

    test_queries = [
        ("crm_1", "cont_101", "ord_101"),
        ("crm_2", "cnt_201", "ord_201"),
        ("crm_3", "rec_301", "rec_ord_301"),
    ]

    for crm, contact_id, order_id in test_queries:
        agent = SupportAgent(client=client, target_crm=crm)
        print(f"\n  {YELLOW}▶ Running SupportAgent against {crm.upper()}...{RESET}")

        # Tool 1: get_contact
        contact = agent.execute_tool("get_contact", {"contact_id": contact_id})
        assert contact.id == contact_id
        print_success(f"Tool 'get_contact' succeeded -> Canonical Contact: {contact.first_name} {contact.last_name} ({contact.company})")
        print_detail("Contact ID", contact.id)
        print_detail("Email", contact.email)

        # Tool 2: check_order
        order = agent.execute_tool("check_order", {"order_id": order_id})
        assert order.id == order_id
        print_success(f"Tool 'check_order' succeeded -> Canonical Order: {order.id} | Total: ${order.total_amount:.2f} {order.currency} | Status: {order.status}")
        print_detail("Items Count", len(order.items))
        print_detail("Shipping Destination", order.shipping_address)

        total_checks += 2

    # =========================================================================
    # Step 2: SchedulingAgent Operations Across All 3 CRMs
    # =========================================================================
    print_section("2. SchedulingAgent Lead Creation & Calendar Booking Across CRMs")

    sched_targets = ["crm_1", "crm_2", "crm_3"]
    for crm in sched_targets:
        agent = SchedulingAgent(client=client, target_crm=crm)
        print(f"\n  {YELLOW}▶ Running SchedulingAgent against {crm.upper()}...{RESET}")

        lead_email = f"lead.{crm}@enterprise.com"
        contact = agent.execute_tool(
            "create_contact",
            {
                "contact_data": {
                    "first_name": "Sarah",
                    "last_name": "Connor",
                    "email": lead_email,
                    "phone": "+1-555-0800",
                    "company": "Cyberdyne Systems",
                }
            },
        )
        assert contact.email == lead_email
        print_success(f"Tool 'create_contact' succeeded -> Generated Contact ID: {contact.id}")

        slot_id = f"demo_slot_{crm}"
        slot = agent.execute_tool(
            "book_slot",
            {
                "slot_id": slot_id,
                "attendee_email": lead_email,
                "title": "Onboarding Architecture Review",
            },
        )
        assert slot.status == "confirmed"
        print_success(f"Tool 'book_slot' succeeded -> Slot ID: {slot.id} | Status: {slot.status}")
        print_detail("Slot Time Window", f"{slot.start_time.isoformat()} to {slot.end_time.isoformat()}")

        total_checks += 2

    # =========================================================================
    # Step 3: BillingAgent Operations Across All 3 CRMs
    # =========================================================================
    print_section("3. BillingAgent Payments & Invoicing Across CRMs")

    billing_targets = [
        ("crm_1", "cont_101", "ord_101", 199.99, "card_visa"),
        ("crm_2", "cnt_201", "ord_201", 450.00, "tok_mastercard"),
        ("crm_3", "rec_301", "rec_ord_301", 320.50, "corporate_ach"),
    ]

    for crm, contact_id, order_id, amount, payment_method in billing_targets:
        agent = BillingAgent(client=client, target_crm=crm)
        print(f"\n  {YELLOW}▶ Running BillingAgent against {crm.upper()}...{RESET}")

        # Tool 1: get_orders by contact ID
        orders = agent.execute_tool("get_orders", {"contact_id": contact_id})
        assert len(orders) >= 1
        assert orders[0].id == order_id
        print_success(f"Tool 'get_orders' for contact {contact_id} succeeded -> Located {len(orders)} order(s)")

        order = agent.execute_tool("check_order", {"order_id": order_id})
        assert order.id == order_id
        print_success(f"Verified Order {order.id} total: ${order.total_amount:.2f}")

        payment = agent.execute_tool(
            "take_payment",
            {
                "order_id": order_id,
                "amount": amount,
                "currency": "USD",
                "payment_method": payment_method,
            },
        )
        assert payment.status == "completed"
        print_success(f"Tool 'take_payment' succeeded -> Payment ID: {payment.id} | Amount: ${payment.amount:.2f} | Status: {payment.status}")
        print_detail("Payment Method", payment.payment_method)

        total_checks += 3

    # =========================================================================
    # Step 4: Canonical Error Normalization & Self-Healing
    # =========================================================================
    print_section("4. Canonical Error Interception, Normalization & Self-Healing")

    # 4.1 EntityNotFoundError
    print(f"\n  {YELLOW}▶ Scenario A: EntityNotFoundError (404 Normalization){RESET}")
    for crm in ["crm_1", "crm_2", "crm_3"]:
        err_dict = client.dispatch_tool_call(
            "get_contact",
            {"contact_id": "nonexistent_contact_id"},
            target_crm=crm,
        )
        assert err_dict.get("error") is True
        assert err_dict.get("error_type") == "EntityNotFoundError"
        assert err_dict.get("target_crm") == crm
        print_success(f"Intercepted missing contact on {crm.upper()} -> Normalized to {BOLD}{err_dict['error_type']}{RESET}")
        print_detail("Normalized Message", err_dict["message"])
        total_checks += 1

    # 4.2 SlotConflictError
    print(f"\n  {YELLOW}▶ Scenario B: SlotConflictError (409 Conflict Normalization){RESET}")
    conflict_slots = [
        ("crm_1", "slot_conflict"),
        ("crm_2", "slot_conflict"),
        ("crm_3", "rec_slot_conflict"),
    ]
    for crm, conflict_id in conflict_slots:
        err_dict = client.dispatch_tool_call(
            "book_slot",
            {
                "slot_id": conflict_id,
                "attendee_email": "candidate@example.com",
                "title": "Colliding Appointment",
            },
            target_crm=crm,
        )
        assert err_dict.get("error") is True
        assert err_dict.get("error_type") == "SlotConflictError"
        assert err_dict.get("target_crm") == crm
        print_success(f"Intercepted booking collision on {crm.upper()} ({conflict_id}) -> Normalized to {BOLD}{err_dict['error_type']}{RESET}")
        print_detail("Normalized Message", err_dict["message"])
        total_checks += 1

    # 4.3 PaymentFailedError & Self-Healing
    print(f"\n  {YELLOW}▶ Scenario C: PaymentFailedError (402 Decline Normalization & Recovery){RESET}")
    declined_methods = [
        ("crm_1", "card_declined", "card_visa"),
        ("crm_2", "tok_declined", "tok_mastercard"),
        ("crm_3", "declined_ach", "corporate_ach"),
    ]
    billing_crm = BillingAgent(client=client)
    for crm, decl_method, valid_method in declined_methods:
        err_dict = client.dispatch_tool_call(
            "take_payment",
            {
                "order_id": "ord_101" if crm == "crm_1" else ("ord_201" if crm == "crm_2" else "rec_ord_301"),
                "amount": 99.00,
                "payment_method": decl_method,
            },
            target_crm=crm,
        )
        assert err_dict.get("error") is True
        assert err_dict.get("error_type") == "PaymentFailedError"
        print_success(f"Intercepted payment decline on {crm.upper()} -> Normalized to {BOLD}{err_dict['error_type']}{RESET}")
        print_detail("Decline Reason", err_dict["message"])

        # Agent self-healing: recovery with valid payment method
        recovery = client.dispatch_tool_call(
            "take_payment",
            {
                "order_id": "ord_101" if crm == "crm_1" else ("ord_201" if crm == "crm_2" else "rec_ord_301"),
                "amount": 99.00,
                "payment_method": valid_method,
            },
            target_crm=crm,
        )
        assert recovery.status == "completed"
        print_success(f"Agent recovered gracefully with alternative method '{valid_method}' -> Status: {BOLD}{recovery.status}{RESET}")
        total_checks += 3

    # =========================================================================
    # Final Summary
    # =========================================================================
    print(f"\n{GREEN}{BOLD}" + "=" * 80)
    print("   ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY")
    print(f"   Total Assertions Verified: {total_checks} across CRM 1, CRM 2, and CRM 3")
    print("=" * 80 + f"{RESET}\n")

    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
