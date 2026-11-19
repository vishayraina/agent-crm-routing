# Centralized Routing Layer with Adapter Pattern

We decided to build a centralized Routing Layer service using the Adapter Pattern and explicit target CRM routing, accessed via a singular lightweight Client SDK.

## Context

Multiple internal agentic applications need to interact with several heterogeneous CRMs (Mock CRM 1, 2, and 3), each having disparate API conventions, authentication methods, and entity schemas. Directly integrating each agent with every CRM would cause N x M coupling, require duplicated transformation code across agent codebases, and leak provider-specific quirks into AI prompt and tool definitions.

## Decision

1. **Centralized Routing Layer**: Provide a singular REST service that handles bidirectional transformation and protocol dispatch.
2. **Adapter Pattern**: Implement isolated adapters per CRM provider in the routing layer to map Canonical Models to provider schemas and vice versa.
3. **Explicit Targeting**: The Client SDK passes an explicit target CRM identifier (e.g. `crm_1`, `crm_2`, `crm_3`) to keep the routing layer stateless and deterministic.
4. **Lightweight Client SDK**: Agent applications only interact with canonical types and methods, remaining agnostic to CRM-specific implementations.

