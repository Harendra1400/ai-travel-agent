"""MCP tool classification and approval policy."""

from dataclasses import dataclass

from app.core.config import MCPToolSettings, Settings
from app.db.models.enums import ToolRisk


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """Immutable policy applied before exposing a tool to an agent."""

    server: str
    tool: str
    risk: ToolRisk
    required_scopes: frozenset[str]

    @property
    def requires_human_approval(self) -> bool:
        """Write and financial actions may never execute autonomously."""
        return self.risk in {ToolRisk.WRITE, ToolRisk.FINANCIAL}


class ToolNotAllowedError(ValueError):
    """Raised when an agent requests a tool outside the configured allow-list."""


def resolve_tool_policy(settings: Settings, server: str, tool: str) -> ToolPolicy:
    """Resolve one exact allow-list entry; deny everything else by default."""
    configured: MCPToolSettings | None = next(
        (
            item
            for item in settings.mcp_tools
            if item.server == server and item.tool == tool
        ),
        None,
    )
    if configured is None:
        raise ToolNotAllowedError(f"Tool is not allowed: {server}/{tool}")
    return ToolPolicy(
        server=server,
        tool=tool,
        risk=ToolRisk(configured.risk),
        required_scopes=frozenset(configured.required_scopes),
    )
