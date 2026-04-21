# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Mock MCP Server
# A lightweight MCP server that simulates enterprise data tools for
# end-to-end testing of the Core Intelligence reasoning pipeline.
#
# Exposes tools:  sql_query · notion_search · billing_adjust · subscription_status
# Transport:      HTTP (Streamable HTTP) on port 8100
# Protocol:       JSON-RPC 2.0 (MCP specification)
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict
from random import randint

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mock_mcp_server")

app = FastAPI(title="Mock MCP Server", version="1.0.0")

# ── Simulated Enterprise Data ────────────────────────────────────────────────

MOCK_BILLING = [
    {"id": "INV-2026-001", "customer": "Acme Corp",   "amount": 12500.00, "status": "paid",    "date": "2026-04-01"},
    {"id": "INV-2026-002", "customer": "Globex Inc",   "amount": 8750.00,  "status": "pending", "date": "2026-04-10"},
    {"id": "INV-2026-003", "customer": "Initech LLC",  "amount": 23000.00, "status": "overdue", "date": "2026-03-15"},
    {"id": "INV-2026-004", "customer": "Soylent Corp", "amount": 5200.00,  "status": "paid",    "date": "2026-04-18"},
]

MOCK_SUBSCRIPTIONS = [
    {"id": "SUB-001", "customer": "Acme Corp",   "plan": "Enterprise", "status": "active",    "renewal": "2026-12-01"},
    {"id": "SUB-002", "customer": "Globex Inc",   "plan": "Pro",        "status": "active",    "renewal": "2026-09-15"},
    {"id": "SUB-003", "customer": "Initech LLC",  "plan": "Enterprise", "status": "cancelled", "renewal": "N/A"},
    {"id": "SUB-004", "customer": "Soylent Corp", "plan": "Starter",    "status": "active",    "renewal": "2026-06-01"},
]

MOCK_NOTION_PAGES = [
    {"id": "page-001", "title": "Q2 2026 OKRs",                "content": "Objective: Achieve 80% autonomous resolution rate. KR1: Deploy RAGless engine. KR2: TTFA < 300ms. KR3: 98% groundedness."},
    {"id": "page-002", "title": "Incident Postmortem — Apr 12", "content": "Root cause: MCP server timeout under high load. Resolution: Added circuit breaker with 5s timeout. Impact: 12 min downtime."},
    {"id": "page-003", "title": "Voice Pipeline Architecture",  "content": "WebRTC over UDP for zero-latency. Gemini 2.0 Flash for native audio reasoning. Barge-in via energy-threshold VAD."},
    {"id": "page-004", "title": "Self-Healing QA Runbook",      "content": "Step 1: Fingerprint all UI elements. Step 2: Run nightly drift detection. Step 3: Auto-apply patches with confidence > 0.85."},
]

# ── Tool Definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "sql_query",
        "description": "Execute a read-only SQL query against the enterprise PostgreSQL database. Returns tabular results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The SQL SELECT query to execute"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "notion_search",
        "description": "Search Notion workspace pages by keyword. Returns matching page titles and content snippets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "billing_adjust",
        "description": "Apply a credit or adjustment to a customer's billing record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "The invoice ID to adjust"},
                "adjustment_amount": {"type": "number", "description": "Amount to credit (negative) or charge (positive)"},
                "reason": {"type": "string", "description": "Reason for the adjustment"},
            },
            "required": ["invoice_id", "adjustment_amount", "reason"],
        },
    },
    {
        "name": "subscription_status",
        "description": "Check or update the status of a customer's subscription.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer": {"type": "string", "description": "Customer name to look up"},
            },
            "required": ["customer"],
        },
    },
]


# ── JSON-RPC Handler ─────────────────────────────────────────────────────────

@app.post("/")
async def jsonrpc_handler(request: Request):
    """Handle all MCP JSON-RPC 2.0 requests on a single endpoint."""
    body = await request.json()
    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    logger.info("← %s (id=%s)", method, req_id)

    if method == "initialize":
        return _success(req_id, {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "mock-enterprise-data", "version": "1.0.0"},
        })

    if method == "tools/list":
        return _success(req_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        return _handle_tool_call(req_id, tool_name, arguments)

    if method == "resources/read":
        uri = params.get("uri", "")
        return _handle_resource_read(req_id, uri)

    return _error(req_id, -32601, f"Method not found: {method}")


# ── Tool Execution ───────────────────────────────────────────────────────────

def _handle_tool_call(req_id, tool_name: str, arguments: Dict[str, Any]):
    """Route tool calls to the appropriate mock handler."""
    logger.info("  → tool: %s, args: %s", tool_name, arguments)

    if tool_name == "sql_query":
        return _exec_sql_query(req_id, arguments.get("query", ""))

    if tool_name == "notion_search":
        return _exec_notion_search(req_id, arguments.get("query", ""))

    if tool_name == "billing_adjust":
        return _exec_billing_adjust(req_id, arguments)

    if tool_name == "subscription_status":
        return _exec_subscription_status(req_id, arguments.get("customer", ""))

    return _success(req_id, {
        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
        "isError": True,
    })


def _exec_sql_query(req_id, query: str):
    """Simulate SQL query execution against mock data."""
    q = query.lower()

    if "billing" in q or "invoice" in q:
        data = MOCK_BILLING
    elif "subscription" in q:
        data = MOCK_SUBSCRIPTIONS
    elif "health_check" in q or "select 1" in q:
        data = [{"health": "ok", "timestamp": datetime.now().isoformat()}]
    else:
        data = [{"message": f"Query executed: {query}", "rows_affected": 0}]

    result_text = json.dumps(data, indent=2)
    logger.info("  ✓ sql_query returned %d records", len(data))
    return _success(req_id, {
        "content": [{"type": "text", "text": result_text}],
        "isError": False,
    })


def _exec_notion_search(req_id, query: str):
    """Search mock Notion pages by keyword."""
    q = query.lower()
    matches = [
        p for p in MOCK_NOTION_PAGES
        if q in p["title"].lower() or q in p["content"].lower()
    ]
    if not matches:
        matches = MOCK_NOTION_PAGES[:2]  # Return top 2 as fallback

    result_text = json.dumps(matches, indent=2)
    logger.info("  ✓ notion_search found %d pages", len(matches))
    return _success(req_id, {
        "content": [{"type": "text", "text": result_text}],
        "isError": False,
    })


def _exec_billing_adjust(req_id, args: Dict[str, Any]):
    """Simulate a billing adjustment (transactional action)."""
    invoice_id = args.get("invoice_id", "")
    amount = args.get("adjustment_amount", 0)
    reason = args.get("reason", "")

    # Find the invoice
    invoice = next((b for b in MOCK_BILLING if b["id"] == invoice_id), None)
    if not invoice:
        return _success(req_id, {
            "content": [{"type": "text", "text": f"Invoice {invoice_id} not found."}],
            "isError": True,
        })

    new_amount = invoice["amount"] + amount
    result = {
        "invoice_id": invoice_id,
        "customer": invoice["customer"],
        "original_amount": invoice["amount"],
        "adjustment": amount,
        "new_amount": new_amount,
        "reason": reason,
        "status": "adjustment_applied",
        "timestamp": datetime.now().isoformat(),
    }

    logger.info("  ✓ billing_adjust: %s → $%.2f (adj: $%.2f)", invoice_id, new_amount, amount)
    return _success(req_id, {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
        "isError": False,
    })


def _exec_subscription_status(req_id, customer: str):
    """Look up subscription status for a customer."""
    c = customer.lower()
    matches = [s for s in MOCK_SUBSCRIPTIONS if c in s["customer"].lower()]

    if not matches:
        return _success(req_id, {
            "content": [{"type": "text", "text": f"No subscription found for '{customer}'."}],
            "isError": True,
        })

    result_text = json.dumps(matches, indent=2)
    logger.info("  ✓ subscription_status: found %d records for '%s'", len(matches), customer)
    return _success(req_id, {
        "content": [{"type": "text", "text": result_text}],
        "isError": False,
    })


def _handle_resource_read(req_id, uri: str):
    """Handle resource read requests."""
    return _success(req_id, {
        "contents": [{
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"Resource content for: {uri}",
        }],
    })


# ── JSON-RPC Response Helpers ────────────────────────────────────────────────

def _success(req_id, result):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

def _error(req_id, code: int, message: str):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


# ── Standalone ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
