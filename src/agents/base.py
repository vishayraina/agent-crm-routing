from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from src.domain.contracts import CrmClientProtocol
from src.domain.tools import ALL_TOOLS


class BaseAgent(ABC):
    """Abstract base class for all Mock Agents."""

    declared_tools: list[str] = []

    def __init__(
        self,
        client: CrmClientProtocol,
        target_crm: str | None = None,
    ) -> None:
        self.client = client
        self.target_crm = target_crm

    def get_tools(self) -> list[dict[str, Any]]:
        """Return the standard tool declaration schemas exposed to LLM context for this agent."""
        return [ALL_TOOLS[name] for name in self.declared_tools if name in ALL_TOOLS]

    def get_tool_names(self) -> list[str]:
        """Return the list of tool names supported by this agent."""
        return list(self.declared_tools)

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
    ) -> Any:
        """Validate and dispatch a tool execution to the client contract."""
        if name not in self.declared_tools:
            raise ValueError(f"Tool '{name}' is not supported by {self.__class__.__name__}. Supported: {self.declared_tools}")

        effective_crm = target_crm or self.target_crm
        if hasattr(self.client, "dispatch_tool_call"):
            return self.client.dispatch_tool_call(name, arguments, target_crm=effective_crm)

        # Fallback to direct method invocation on client
        method = getattr(self.client, name)
        kwargs = dict(arguments)
        if "target_crm" not in kwargs:
            kwargs["target_crm"] = effective_crm
        return method(**kwargs)

    @abstractmethod
    def run_deterministic_flow(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute a predefined deterministic test sequence of tool calls."""
        ...
