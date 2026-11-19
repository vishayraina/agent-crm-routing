# 01: Canonical Domain Contracts & Skeletal Mock Agents

**What to build:**
Define the canonical domain models representing Contacts, Orders, Appointment Slots, Payments, and Canonical Errors. Implement the three skeletal Mock Agent classes (Support Agent, Scheduling Agent, and Billing Agent) that specify their tool declarations and execute deterministic test calls against a client contract.

**Blocked by:**
None (can start immediately)

**Status:** ready-for-agent

- [ ] Pydantic canonical models created for Contact, Order, AppointmentSlot, Payment, and CanonicalError.
- [ ] SupportAgent class created with tool signatures for `get_contact` and `check_order`, plus a deterministic test invocation run.
- [ ] SchedulingAgent class created with tool signatures for `create_contact` and `book_slot`, plus a deterministic test invocation run.
- [ ] BillingAgent class created with tool signatures for `get_contact`, `check_order`, and `take_payment`, plus a deterministic test invocation run.

