# Specification: Agent-to-CRM Routing Platform

## Problem Statement

Internal engineering teams building automated agentic applications face severe integration friction when connecting to heterogeneous CRM systems. Each downstream CRM exposes different API protocols, URL conventions, nested data structures, field names, and error formats. Directly integrating each agent with every CRM creates an N × M coupling nightmare, causes duplicate transformation logic across agent repositories, and leaks vendor-specific idiosyncrasies into agent prompt definitions and tool loops.

## Solution

A centralized Routing Layer and singular Client SDK that normalize all interactions between agentic applications and heterogeneous CRM systems:
- Agent applications import a single, lightweight Client SDK with canonical domain operations (`Contact`, `Order`, `AppointmentSlot`, `Payment`) and ready-to-use LLM tool definitions.
- The Routing Layer uses the Adapter Pattern to dynamically transform incoming canonical requests into the target CRM's native schema (e.g. flat REST for CRM 1, nested RPC for CRM 2, and generic property-bag for CRM 3).
- Downstream failures are intercepted and normalized into structured, typed Canonical Errors so agent reasoning loops can self-heal without parsing vendor-specific error messages.

## User Stories

1. As an agent developer, I want a single client library to interact with all company CRMs, so that I don't have to install and learn multiple vendor SDKs.
2. As an agent developer, I want pre-built LLM tool schemas exported by the SDK, so that I can bind CRM tools to my agent without writing manual schema boilerplate.
3. As an agent developer, I want to route requests to a specific CRM by providing a target identifier, so that multi-tenant routing is deterministic and stateless.
4. As a Support Agent, I want to fetch contact details by ID or email using a canonical contact model, so that I can look up customer context regardless of which CRM stores the record.
5. As a Support Agent, I want to check the fulfillment and shipment status of an order using a canonical order model, so that I can answer customer order status queries.
6. As a Scheduling Agent, I want to create a new contact in the target CRM using a normalized schema, so that inbound leads are properly captured.
7. As a Scheduling Agent, I want to book an appointment slot on a CRM calendar, so that meetings can be scheduled without knowing vendor calendar endpoints.
8. As a Billing Agent, I want to query customer orders and charge payments against them, so that payment collection workflows execute smoothly.
9. As an agent application, I want downstream "not found" responses returned as a typed `EntityNotFoundError`, so that the agent's LLM can inform the user that the entity does not exist.
10. As an agent application, I want booking conflicts returned as a typed `SlotConflictError`, so that the agent can prompt the user to choose an alternative time slot.
11. As an agent application, I want payment declines returned as a typed `PaymentFailedError` with a clear failure reason, so that the agent can ask the user for a new payment method.
12. As a platform engineer, I want all vendor credentials managed inside the Routing Layer, so that third-party CRM API keys are never exposed to agent runtimes.
13. As a platform engineer, I want each CRM's adapter isolated in its own module, so that adding a new CRM provider does not touch existing CRM adapter logic or agent contracts.

## Implementation Decisions

- **Technology Stack**: Python with FastAPI for HTTP services and Pydantic for canonical data modeling and provider schema validation.
- **Architecture**: Centralized Routing Layer HTTP service implementing the Adapter Pattern with explicit CRM target routing (`crm_1`, `crm_2`, `crm_3`).
- **Canonical Models**:
  - `Contact`: normalized fields (`id`, `first_name`, `last_name`, `email`, `phone`, `company`, `created_at`).
  - `Order`: normalized fields (`id`, `contact_id`, `items`, `total_amount`, `currency`, `status`, `shipping_address`).
  - `AppointmentSlot`: normalized fields (`id`, `start_time`, `end_time`, `title`, `attendee_email`, `status`).
  - `Payment`: normalized fields (`id`, `order_id`, `amount`, `currency`, `payment_method`, `status`, `transaction_timestamp`).
  - `CanonicalError`: normalized error response (`error_type`, `message`, `target_crm`, `details`).
- **Target CRM Schemas**:
  - `Mock CRM 1`: Flat REST schema with `snake_case` attributes and ISO-8601 timestamps.
  - `Mock CRM 2`: RPC-style service with camelCase naming, nested records (`customerDetails.contactInfo`), and epoch millisecond timestamps.
  - `Mock CRM 3`: Object-property schema with dynamic property dictionaries (`properties: {...}`).
- **Client SDK**: Dual-surface client exposing typed async/sync methods alongside auto-generated LLM tool definitions and a `dispatch_tool_call` handler.
- **Mock Agents**: Three skeletal agents (`SupportAgent`, `SchedulingAgent`, `BillingAgent`) with tool-calling capabilities executing deterministic test queries.

## Testing Decisions

- **What makes a good test**: Tests must verify end-to-end external behavior at the Client SDK / Tool Calling boundary. Tests must not assert internal adapter helper state or intermediate dictionaries.
- **Tested Modules**: The entire vertical slice: Agent -> Client SDK -> Routing Layer -> Adapters -> Mock CRMs.
- **Error Tests**: Explicit scenarios verifying that 404s, slot conflicts, and payment declines are faithfully translated to Canonical Errors.

## Out of Scope

- Autonomous LLM prompt-generation loops and external OpenAI/Anthropic network calls (mock agents use deterministic tool invocation test calls).
- Persistent relational database storage (mock CRMs use lightweight in-memory test data).
- Production authentication handshakes (OAuth2 token exchanges, webhook subscriptions).
- Distributed rate-limiting and circuit breakers.

## Further Notes

- Architecture complies with ADR 0001 (Centralized Routing Layer with Adapter Pattern) and ADR 0002 (Canonical Error Normalization).
- Terminology strictly adheres to the project domain model in `GLOSSARY.md`.

