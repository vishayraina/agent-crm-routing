# 04: Singular Client SDK & Tool Dispatcher

**What to build:**
Create the singular Client SDK (`CrmClient`) used by all agentic applications to communicate with the Routing Layer. The SDK provides both direct typed methods (e.g. `client.orders.check(order_id)`) with Pydantic return types, and automated LLM function tool exports (`client.get_tools()`) and execution dispatcher (`client.dispatch_tool_call(name, args)`).

**Blocked by:**
03: Central Routing Layer & CRM Provider Adapters

**Status:** ready-for-agent

- [ ] CrmClient class initializes with `base_url` and `crm_target` (e.g. `crm_1`, `crm_2`, `crm_3`).
- [ ] Direct typed methods implemented for `get_contact`, `create_contact`, `check_order`, `book_slot`, and `take_payment`.
- [ ] Tool registry generates standard JSON schemas compatible with LLM function-calling declarations.
- [ ] `dispatch_tool_call(name, arguments)` dispatches tool execution and returns serialized canonical model or structured error JSON.

