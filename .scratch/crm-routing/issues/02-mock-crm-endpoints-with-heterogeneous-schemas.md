# 02: Mock CRM Endpoints with Heterogeneous Schemas

**What to build:**
Create mock HTTP endpoints simulating the three distinct CRM providers with intentionally divergent API conventions and schemas: CRM 1 (flat REST snake_case), CRM 2 (nested RPC camelCase), and CRM 3 (property-bag generic records). Each mock returns deterministic responses for Contacts, Orders, Appointment Slots, and Payments, as well as provider-specific error responses for edge cases.

**Blocked by:**
None (can start immediately)

**Status:** completed

- [x] Mock CRM 1 implemented with flat snake_case REST endpoints (`/crm1/contacts`, `/crm1/orders/{id}`, `/crm1/slots/book`, `/crm1/payments/charge`).
- [x] Mock CRM 2 implemented with nested camelCase RPC endpoints (`/crm2/api/v2/getContact`, `/crm2/api/v2/fetchOrder`, `/crm2/api/v2/execBooking`, `/crm2/api/v2/processCharge`).
- [x] Mock CRM 3 implemented with property-bag object endpoints (`/crm3/objects/contacts`, `/crm3/objects/orders/{id}`, `/crm3/objects/appointments`, `/crm3/objects/transactions`).
- [x] Provider-specific error fixtures included (e.g. 404 contact not found, 409 slot clash, 402 card declined) reflecting each CRM's unique format.

