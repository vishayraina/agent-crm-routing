# 05: End-to-End Test Suite & Verification Runner

**What to build:**
Create an automated test suite and demo runner that spins up the Mock CRM server and Routing Layer service, injects the Client SDK into the three Mock Agents, executes each agent's deterministic tool calls across the different CRM targets, and asserts that all canonical data transformations and normalized error handlings succeed end-to-end.

**Blocked by:**
01: Canonical Domain Contracts & Skeletal Mock Agents
04: Singular Client SDK & Tool Dispatcher

**Status:** completed

- [x] End-to-end test executes SupportAgent queries (`get_contact`, `check_order`) against CRM 1, CRM 2, and CRM 3.
- [x] End-to-end test executes SchedulingAgent operations (`create_contact`, `book_slot`) against CRM 1, CRM 2, and CRM 3.
- [x] End-to-end test executes BillingAgent operations (`check_order`, `take_payment`) against CRM 1, CRM 2, and CRM 3.
- [x] Negative test cases verify that downstream CRM errors (not found, slot conflict, payment decline) are cleanly normalized into canonical errors.
- [x] Single executable test runner (`pytest` or script) validates the entire system in CI and local dev.

