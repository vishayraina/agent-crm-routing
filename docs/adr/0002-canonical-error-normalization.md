# Canonical Error Normalization for Agent Tool Execution

We decided to normalize all downstream CRM HTTP errors and vendor-specific failure bodies into a standardized Canonical Error schema across the Routing Layer and Client SDK.

## Context

Downstream CRMs communicate failures using widely divergent formats (e.g., HTTP 404 with HTML bodies, HTTP 422 with nested validation arrays, HTTP 200 with `status: "FAILED"`, or vendor-specific error codes). When agentic applications execute tool calls, raw vendor errors degrade LLM reasoning, pollute context windows with irrelevant provider JSON, and make programmatic fallback/retry logic fragile.

## Decision

The Routing Layer adapters map provider-specific failure modes into a typed hierarchy of Canonical Errors (`EntityNotFoundError`, `SlotConflictError`, `PaymentFailedError`, `ValidationError`, and `ProviderUnavailableError`). The Client SDK surfaces these as structured, self-describing tool call results so agents can directly reason over failures and suggest corrective actions to users.

