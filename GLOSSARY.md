# Agent-to-CRM Routing Platform

A unified platform and client abstraction that allows internal agentic applications to interact with heterogeneous CRM systems through a standardized canonical interface.

## Language

**Routing Layer**:
The central service that receives canonical requests from agentic applications, determines the target CRM, and dispatches requests to provider adapters.
_Avoid_: Gateway, proxy, message broker

**Client SDK**:
The singular client library imported by agentic applications to interact with the Routing Layer using canonical domain models and methods.
_Avoid_: Driver, connector, wrapper

**Target CRM**:
The specific downstream CRM provider or tenant destination (`crm_1`, `crm_2`, `crm_3`) identified in a request.
_Avoid_: Destination, vendor, backend

**CRM Adapter**:
A provider-specific module within the Routing Layer responsible for bidirectional translation between canonical models and provider-specific schemas.
_Avoid_: Translator, converter, plugin

**Canonical Model**:
The unified, normalized domain schema exposed to agentic applications, shielding them from provider-specific idiosyncrasies.
_Avoid_: Common schema, generic payload

**Canonical Error**:
A normalized failure structure returned by the Routing Layer that translates provider-specific HTTP codes and payloads into uniform error categories for agent reasoning.
_Avoid_: Provider error, upstream failure, raw exception

**Tool Definition**:
A standardized function specification and schema exported by the Client SDK that an agentic application binds to its LLM context.
_Avoid_: Action, skill, function call

**Agentic Application**:
An internal automated software agent that uses tool calling to perform business actions in a CRM on behalf of users or workflows.
_Avoid_: Bot, caller, client app

**Contact**:
A person or lead record maintained within a CRM.
_Avoid_: Lead, user, customer, account

**Order**:
A customer purchase or transaction record queried for fulfillment and billing status.
_Avoid_: Invoice, purchase, transaction

**Appointment Slot**:
A reservable window of time on a CRM schedule or calendar.
_Avoid_: Booking window, meeting time, availability

**Payment**:
A monetary transaction collected or processed against an order or customer balance.
_Avoid_: Settlement, charge, checkout
