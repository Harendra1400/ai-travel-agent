"""Hardened client boundary for allow-listed MCP tool execution."""

import json
import os
from datetime import timedelta

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.core.config import Settings
from app.mcp_gateway.policy import ToolPolicy, resolve_tool_policy


class MCPGateway:
    """Connect to configured MCP servers without persisting bearer credentials."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def policy(self, server: str, tool: str) -> ToolPolicy:
        """Return the centrally configured policy for a tool."""
        return resolve_tool_policy(self._settings, server, tool)

    async def call_tool(
        self,
        *,
        server: str,
        tool: str,
        arguments: dict[str, object],
        user_id: str,
        run_id: str,
    ) -> dict[str, object]:
        """Execute one previously authorized call over MCP streamable HTTP."""
        self.policy(server, tool)
        server_settings = self._settings.mcp_servers[server]
        headers: dict[str, str] = {}
        if server_settings.authorization_env_var:
            token = os.environ.get(server_settings.authorization_env_var)
            if not token:
                raise RuntimeError(
                    "MCP authorization secret is not available in the environment"
                )
            headers["Authorization"] = f"Bearer {token}"

        timeout = self._settings.mcp_timeout_seconds
        async with (
            httpx.AsyncClient(headers=headers, timeout=timeout) as client,
            streamable_http_client(
                str(server_settings.url),
                http_client=client,
            ) as (read_stream, write_stream, _),
            ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=timeout),
            ) as session,
        ):
            await session.initialize()
            result = await session.call_tool(
                tool,
                arguments,
                meta={"user_id": user_id, "agent_run_id": run_id},
            )
        payload: dict[str, object] = result.model_dump(
            mode="json",
            exclude_none=True,
        )
        serialized_size = len(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        if serialized_size > self._settings.mcp_max_response_bytes:
            raise ValueError("MCP response exceeds the configured size limit")
        return payload
