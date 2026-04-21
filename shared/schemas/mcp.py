# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Model Context Protocol (MCP) Schemas
# The universal "USB-C for data" — standardized contracts for tool discovery,
# invocation, and resource access across enterprise SQL & Notion databases.
# Spec: JSON-RPC 2.0 over stdio / SSE / Streamable HTTP
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Tool Discovery ───────────────────────────────────────────────────────────

class MCPToolParameter(BaseModel):
    """Schema for a single parameter accepted by an MCP tool."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="JSON Schema type (string, integer, object, …)")
    description: str = Field(default="", description="Human-readable purpose")
    required: bool = Field(default=False)


class MCPTool(BaseModel):
    """Describes a single capability exposed by an MCP server."""
    name: str = Field(..., description="Unique tool identifier, e.g. 'sql_query'")
    description: str = Field(..., description="What the tool does")
    inputSchema: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full JSON Schema for the tool's input",
    )
    parameters: List[MCPToolParameter] = Field(
        default_factory=list,
        description="Structured parameter list (convenience view)",
    )


class ListToolsResult(BaseModel):
    """Response from `tools/list` — enumerates available tools on a server."""
    tools: List[MCPTool]


# ── Tool Invocation ──────────────────────────────────────────────────────────

class CallToolRequest(BaseModel):
    """
    JSON-RPC request to invoke a tool on an MCP server.
    Maps to the `tools/call` method in the MCP specification.
    """
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = "tools/call"
    params: Dict[str, Any] = Field(
        ...,
        description="Must contain 'name' (tool id) and 'arguments' (dict)",
    )


class ContentBlock(BaseModel):
    """A single content block inside a tool result (text, image, resource)."""
    type: str = Field(..., description="text | image | resource")
    text: Optional[str] = None
    data: Optional[str] = None          # base64 for images
    mimeType: Optional[str] = None
    uri: Optional[str] = None           # for resource references


class CallToolResult(BaseModel):
    """
    Response from a `tools/call` invocation.
    Contains one or more content blocks and an error flag.
    """
    content: List[ContentBlock] = Field(default_factory=list)
    isError: bool = False


# ── Resource Access ──────────────────────────────────────────────────────────

class ReadResourceRequest(BaseModel):
    """JSON-RPC request to read an enterprise resource (database row, doc, …)."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = "resources/read"
    params: Dict[str, Any] = Field(
        ...,
        description="Must contain 'uri' pointing to the target resource",
    )


class ResourceContent(BaseModel):
    """A single resource payload returned by the server."""
    uri: str
    mimeType: str = "text/plain"
    text: Optional[str] = None


class ReadResourceResult(BaseModel):
    """Response from `resources/read`."""
    contents: List[ResourceContent] = Field(default_factory=list)


# ── Server Metadata ──────────────────────────────────────────────────────────

class MCPServerInfo(BaseModel):
    """Advertised capabilities of a connected MCP server."""
    name: str
    version: str
    protocol_version: str = "2025-03-26"
    capabilities: Dict[str, Any] = Field(default_factory=dict)
