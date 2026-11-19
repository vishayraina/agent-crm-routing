# 03: Central Routing Layer & CRM Provider Adapters

**What to build:**
Create the central Routing Layer FastAPI application and provider-specific adapter implementations. The service exposes canonical endpoints for Contacts, Orders, Appointment Slots, and Payments, identifies the target CRM from the incoming request (`X-CRM-Target` header or parameter), translates canonical requests to downstream CRM payloads, invokes the target mock CRM, transforms the response back into canonical models, and normalizes all downstream failures into Canonical Errors.

**Blocked by:**
01: Canonical Domain Contracts & Skeletal Mock Agents
02: Mock CRM Endpoints with Heterogeneous Schemas

**Status:** completed

- [x] Routing Layer FastAPI service exposes `/api/v1/contacts`, `/api/v1/orders/{order_id}`, `/api/v1/slots/book`, `/api/v1/payments/charge`.
- [x] Base adapter interface defined with bidirectional mapping methods for all four domain operations.
- [x] CRM1Adapter transforms canonical models to/from flat snake_case schemas.
- [x] CRM2Adapter transforms canonical models to/from nested camelCase RPC schemas.
- [x] CRM3Adapter transforms canonical models to/from generic property-bag schemas.
- [x] Downstream error mapper translates 4xx/5xx responses into typed CanonicalError responses (`EntityNotFoundError`, `SlotConflictError`, `PaymentFailedError`).
