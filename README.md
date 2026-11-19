# Agent-to-CRM Routing Platform

A centralized routing layer and singular client SDK that normalizes all interactions between autonomous AI agents and heterogeneous downstream Customer Relationship Management (CRM) systems.

## Architecture Overview

```
                                 ┌───────────────────────┐
                                 │   Agent Application   │
                                 │ (Support, Scheduling, │
                                 │        Billing)       │
                                 └──────────┬────────────┘
                                            │ Tool Calls / SDK
                                            ▼
                                 ┌───────────────────────┐
                                 │   CrmClient SDK       │
                                 │ (Canonical Contracts) │
                                 └──────────┬────────────┘
                                            │ HTTP / JSON
                                            ▼
                                 ┌───────────────────────┐
                                 │ Central Routing Layer │
                                 │     (FastAPI App)     │
                                 └──────────┬────────────┘
                       ┌────────────────────┼────────────────────┐
                       ▼                    ▼                    ▼
             ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
             │   CRM1 Adapter   │ │   CRM2 Adapter   │ │   CRM3 Adapter   │
             │   (Flat REST)    │ │   (Nested RPC)   │ │  (Property-Bag)  │
             └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                      │                    │                    │
                      ▼                    ▼                    ▼
             ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
             │    Mock CRM 1    │ │    Mock CRM 2    │ │    Mock CRM 3    │
             └──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Core Design Principles
1. **Centralized Routing with Adapter Pattern (ADR 0001)**: Agents communicate exclusively using canonical schemas (`Contact`, `Order`, `AppointmentSlot`, `Payment`). Provider-specific adapters translate canonical requests into vendor-specific schemas and back.
2. **Canonical Error Normalization (ADR 0002)**: Downstream failures (404 Not Found, 409 Slot Conflict, 402 Payment Declined) are intercepted and translated into typed, structured errors (`EntityNotFoundError`, `SlotConflictError`, `PaymentFailedError`). Both typed exceptions and structured error dictionaries are supported for deterministic agent self-healing.
3. **Singular Client SDK**: Unified client interface providing both typed method access (and namespace helpers) and an LLM `dispatch_tool_call` entrypoint with ready-to-use schemas.

## Project Structure

```
├── docs/                   # Architecture decision records & specifications
│   ├── adr/
│   │   ├── 0001-centralized-routing-layer-with-adapter-pattern.md
│   │   └── 0002-canonical-error-normalization.md
│   └── spec.md
├── run_demo.py             # Executable live verification demo runner
├── scripts/
│   └── run_demo.py         # Subdirectory wrapper for verification runner
├── src/
│   ├── domain/             # Canonical Pydantic models, errors, and tool schemas
│   │   ├── models.py
│   │   ├── errors.py
│   │   ├── contracts.py
│   │   └── tools.py
│   ├── agents/             # Mock autonomous agents
│   │   ├── base.py
│   │   ├── support.py
│   │   ├── scheduling.py
│   │   └── billing.py
│   ├── client/             # Singular Client SDK & tool dispatcher
│   │   └── crm_client.py
│   ├── routing/            # Central Routing Layer FastAPI service & adapters
│   │   ├── app.py
│   │   └── adapters/
│   └── mock_crms/          # Heterogeneous downstream CRM mock implementations
│       ├── crm1.py         # Flat REST API
│       ├── crm2.py         # RPC-style API with nested payloads
│       ├── crm3.py         # Property-bag dynamic entity API
│       └── data.py         # In-memory test dataset & reset utility
└── tests/                  # Automated test suites
    ├── test_canonical_errors.py
    ├── test_domain_models.py
    ├── test_mock_agents.py
    ├── test_mock_crms.py
    ├── test_routing_layer.py
    ├── test_client_sdk.py
    └── test_end_to_end.py  # Full vertical stack integration & verification suite
```

## Running the Verification Runner

Execute the live terminal demo runner to observe agents querying contacts, scheduling calendar slots, processing payments, and recovering from normalized errors across all three heterogeneous CRMs:

```bash
# From repository root:
python run_demo.py

# Or via the scripts directory:
python scripts/run_demo.py
```

## Running the Automated Test Suite

Run the full pytest suite (including unit, routing, client SDK, and end-to-end integration tests):

```bash
pytest -v
```

To run only the end-to-end integration test suite:

```bash
pytest -v tests/test_end_to_end.py
```
