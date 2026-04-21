# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — MCP Client
# Asynchronous JSON-RPC 2.0 client that connects to MCP servers (the
# universal "USB-C for data") for tool discovery, invocation, and resource
# access against enterprise SQL databases and Notion workspaces.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

# ── Resolve imports from shared schemas (single source of truth) ─────────────
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.schemas.mcp import (
    CallToolRequest,
    CallToolResult,
    ContentBlock,
    ListToolsResult,
    MCPServerInfo,
    MCPTool,
    ReadResourceRequest,
    ReadResourceResult,
    ResourceContent,
)

logger = logging.getLogger("insightdesk.mcp_client")


class MCPClientError(Exception):
    """Raised when an MCP server returns an error or is unreachable."""


class MCPClient:
    """
    Async client for a single MCP server.

    Supports two transport modes:
      • **HTTP/SSE** — for remote MCP servers (Streamable HTTP).
      • **stdio**    — for local subprocess-based MCP servers.

    This implementation covers the HTTP transport used in production.
    """

    def __init__(
        self,
        server_url: str,
        server_name: str = "unknown",
        timeout_s: float = 10.0,
        api_key: Optional[str] = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.server_name = server_name
        self._timeout = timeout_s
        self._headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._request_id = 0
        self._tools_cache: Optional[List[MCPTool]] = None
        self._server_info: Optional[MCPServerInfo] = None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the parsed result."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            t0 = time.perf_counter()
            resp = await client.post(
                self.server_url,
                json=payload,
                headers=self._headers,
            )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            body = resp.json()

            if "error" in body:
                err = body["error"]
                raise MCPClientError(
                    f"MCP error {err.get('code')}: {err.get('message')}"
                )

            logger.debug(
                "MCP ← %s [%s] %.1f ms",
                self.server_name,
                payload.get("method"),
                latency,
            )
            return body.get("result", {})

    # ── Initialization ───────────────────────────────────────────────────────

    async def initialize(self) -> MCPServerInfo:
        """
        Perform the MCP `initialize` handshake.
        Retrieves server capabilities and caches them.
        """
        result = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "InsightDesk-CoreIntelligence",
                    "version": "1.0.0",
                },
            },
        })
        self._server_info = MCPServerInfo(
            name=result.get("serverInfo", {}).get("name", self.server_name),
            version=result.get("serverInfo", {}).get("version", "0.0.0"),
            protocol_version=result.get("protocolVersion", "2025-03-26"),
            capabilities=result.get("capabilities", {}),
        )
        logger.info(
            "MCP server initialized: %s v%s",
            self._server_info.name,
            self._server_info.version,
        )
        return self._server_info

    # ── Tool Discovery ───────────────────────────────────────────────────────

    async def list_tools(self, force_refresh: bool = False) -> List[MCPTool]:
        """
        Discover available tools on the server.
        Results are cached after the first call for performance.
        """
        if self._tools_cache and not force_refresh:
            return self._tools_cache

        result = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        })
        parsed = ListToolsResult(tools=[
            MCPTool(**t) for t in result.get("tools", [])
        ])
        self._tools_cache = parsed.tools
        logger.info(
            "Discovered %d tools on %s: %s",
            len(self._tools_cache),
            self.server_name,
            [t.name for t in self._tools_cache],
        )
        return self._tools_cache

    # ── Tool Invocation ──────────────────────────────────────────────────────

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """
        Invoke a tool by name with the given arguments.
        This is the primary action interface — used by the reasoning engine
        to execute backend operations (billing, diagnostics, SQL queries, …).
        """
        t0 = time.perf_counter()
        result = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        })
        latency = (time.perf_counter() - t0) * 1000

        content_blocks = [
            ContentBlock(**cb) for cb in result.get("content", [])
        ]
        call_result = CallToolResult(
            content=content_blocks,
            isError=result.get("isError", False),
        )
        logger.info(
            "Tool [%s] executed in %.1f ms — error=%s",
            tool_name,
            latency,
            call_result.isError,
        )
        return call_result

    # ── Resource Access ──────────────────────────────────────────────────────

    async def read_resource(self, uri: str) -> ReadResourceResult:
        """
        Read an enterprise resource by URI (e.g. a Notion page, DB record).
        """
        result = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {"uri": uri},
        })
        contents = [
            ResourceContent(**rc) for rc in result.get("contents", [])
        ]
        return ReadResourceResult(contents=contents)

    # ── Convenience ──────────────────────────────────────────────────────────

    async def sql_query(self, query: str) -> CallToolResult:
        """Shorthand for invoking an SQL query tool via MCP."""
        return await self.call_tool("sql_query", {"query": query})

    async def notion_search(self, search_text: str) -> CallToolResult:
        """Shorthand for searching Notion pages via MCP."""
        return await self.call_tool("notion_search", {"query": search_text})


# ── Multi-Server Registry ───────────────────────────────────────────────────

class MCPRegistry:
    """
    Manages connections to multiple MCP servers.
    The reasoning engine queries the registry to find the right server
    for a given tool, enabling the "USB-C for data" abstraction.
    """

    def __init__(self) -> None:
        self._clients: Dict[str, MCPClient] = {}
        self._tool_index: Dict[str, str] = {}  # tool_name → server_name

    def register(self, client: MCPClient) -> None:
        """Register an MCP server client."""
        self._clients[client.server_name] = client

    async def initialize_all(self) -> None:
        """Initialize all registered servers and build the tool index."""
        tasks = [c.initialize() for c in self._clients.values()]
        await asyncio.gather(*tasks)
        await self._rebuild_tool_index()

    async def _rebuild_tool_index(self) -> None:
        """Discover tools from all servers and index them by name."""
        self._tool_index.clear()
        for name, client in self._clients.items():
            tools = await client.list_tools(force_refresh=True)
            for tool in tools:
                self._tool_index[tool.name] = name

        logger.info(
            "MCP tool index: %d tools across %d servers",
            len(self._tool_index),
            len(self._clients),
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Route a tool call to the correct MCP server."""
        server_name = self._tool_index.get(tool_name)
        if not server_name:
            raise MCPClientError(
                f"Tool '{tool_name}' not found in any registered MCP server"
            )
        return await self._clients[server_name].call_tool(tool_name, arguments)

    def available_tools(self) -> List[str]:
        """Return all tool names available across all servers."""
        return list(self._tool_index.keys())
