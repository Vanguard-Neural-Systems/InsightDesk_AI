# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Mock MCP Server
# A production-quality JSON-RPC 2.0 mock server that simulates an enterprise
# data backend.  Provides synthetic tools for SQL queries, Notion search,
# user profile lookup, and billing operations so the Reasoning Engine can
# demonstrate the full Think → Act → Observe loop without a live database.
#
# Runs on port 8100 by default (configurable via MCP_MOCK_PORT env var).
# In production, this is replaced by a real Data Access Gateway.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("insightdesk.mock_mcp")

# ── Synthetic Enterprise Data ────────────────────────────────────────────────

MOCK_USERS = [
    {"id": 1001, "name": "Priya Sharma",    "email": "priya.sharma@acme.co",    "plan": "Enterprise",  "status": "active",   "monthly_spend": 2499.00, "region": "APAC"},
    {"id": 1002, "name": "Alex Chen",       "email": "alex.chen@acme.co",       "plan": "Pro",         "status": "active",   "monthly_spend": 499.00,  "region": "NA"},
    {"id": 1003, "name": "Maria Garcia",    "email": "maria.garcia@acme.co",    "plan": "Enterprise",  "status": "churned",  "monthly_spend": 0.00,    "region": "LATAM"},
    {"id": 1004, "name": "James Wilson",    "email": "james.wilson@acme.co",    "plan": "Starter",     "status": "active",   "monthly_spend": 99.00,   "region": "EU"},
    {"id": 1005, "name": "Aisha Patel",     "email": "aisha.patel@acme.co",     "plan": "Pro",         "status": "suspended","monthly_spend": 0.00,    "region": "APAC"},
    {"id": 1006, "name": "David Kim",       "email": "david.kim@acme.co",       "plan": "Enterprise",  "status": "active",   "monthly_spend": 3200.00, "region": "NA"},
    {"id": 1007, "name": "Sofia Rossi",     "email": "sofia.rossi@acme.co",     "plan": "Pro",         "status": "active",   "monthly_spend": 499.00,  "region": "EU"},
    {"id": 1008, "name": "Ravi Krishnan",   "email": "ravi.krishnan@acme.co",   "plan": "Starter",     "status": "trial",    "monthly_spend": 0.00,    "region": "APAC"},
]

MOCK_INVOICES = [
    {"invoice_id": "INV-2026-0401", "user_id": 1001, "amount": 2499.00, "status": "paid",    "due_date": "2026-04-15", "paid_date": "2026-04-10"},
    {"invoice_id": "INV-2026-0402", "user_id": 1002, "amount": 499.00,  "status": "paid",    "due_date": "2026-04-15", "paid_date": "2026-04-14"},
    {"invoice_id": "INV-2026-0403", "user_id": 1003, "amount": 2499.00, "status": "overdue", "due_date": "2026-03-15", "paid_date": None},
    {"invoice_id": "INV-2026-0404", "user_id": 1004, "amount": 99.00,   "status": "pending", "due_date": "2026-04-30", "paid_date": None},
    {"invoice_id": "INV-2026-0405", "user_id": 1005, "amount": 499.00,  "status": "overdue", "due_date": "2026-03-28", "paid_date": None},
    {"invoice_id": "INV-2026-0406", "user_id": 1006, "amount": 3200.00, "status": "paid",    "due_date": "2026-04-15", "paid_date": "2026-04-12"},
    {"invoice_id": "INV-2026-0407", "user_id": 1007, "amount": 499.00,  "status": "paid",    "due_date": "2026-04-15", "paid_date": "2026-04-15"},
]

MOCK_TICKETS = [
    {"ticket_id": "TKT-4001", "user_id": 1001, "subject": "Cannot access dashboard after SSO update",    "priority": "high",   "status": "open",     "created": "2026-04-20"},
    {"ticket_id": "TKT-4002", "user_id": 1003, "subject": "Request for billing adjustment — double charged", "priority": "critical","status": "escalated","created": "2026-04-18"},
    {"ticket_id": "TKT-4003", "user_id": 1005, "subject": "Account suspended without notification",       "priority": "high",   "status": "open",     "created": "2026-04-19"},
    {"ticket_id": "TKT-4004", "user_id": 1002, "subject": "Feature request: export reports to PDF",       "priority": "low",    "status": "closed",   "created": "2026-04-10"},
    {"ticket_id": "TKT-4005", "user_id": 1008, "subject": "Trial extension request — evaluating for team", "priority": "medium", "status": "open",     "created": "2026-04-21"},
]

MOCK_NOTION_PAGES = [
    {"page_id": "notion-001", "title": "Billing Adjustment Policy",      "content": "When a customer reports a double charge, verify the transaction in the billing system. If confirmed, issue a full refund within 3 business days and apply a 10% courtesy credit to the next invoice. Escalate to Finance if the amount exceeds $5,000."},
    {"page_id": "notion-002", "title": "Account Suspension SOP",         "content": "Accounts are suspended after 60 days of non-payment. Before suspension, 3 automated reminders are sent (Day 30, 45, 55). To reinstate, the customer must clear all outstanding invoices. A suspension notice must be sent 48 hours before action."},
    {"page_id": "notion-003", "title": "Onboarding Checklist — Enterprise","content": "1. Assign dedicated CSM within 24 hours. 2. Schedule kickoff call within 48 hours. 3. Complete SSO/SAML integration. 4. Import historical data via MCP bridge. 5. Run first AI reasoning demo with customer's own data. 6. 30-day health check."},
    {"page_id": "notion-004", "title": "SLA Definitions — 2026",         "content": "Tier 1 (Enterprise): 99.9% uptime, 4-hour response for critical issues, dedicated CSM. Tier 2 (Pro): 99.5% uptime, 8-hour response. Tier 3 (Starter): 99% uptime, 24-hour response. All tiers include access to the AI reasoning engine."},
    {"page_id": "notion-005", "title": "Delinquent Account Procedure",   "content": "After 90 days of non-payment: 1. Final courtesy call from CSM. 2. Account downgraded to read-only. 3. Data export link sent to customer. 4. After 120 days, data is archived. 5. Account marked as churned in CRM. Recovery attempts via win-back campaign at Day 180."},
]

# ── Tool Definitions (MCP Spec) ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "sql_query",
        "description": "Execute a read-only SQL query against the enterprise customer database. Supports tables: users, invoices, support_tickets. Returns tabular results as JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL SELECT query to execute"}
            },
            "required": ["query"]
        },
        "parameters": [
            {"name": "query", "type": "string", "description": "SQL SELECT query to execute", "required": True}
        ]
    },
    {
        "name": "notion_search",
        "description": "Search the company Notion knowledge base for policies, SOPs, and documentation. Returns matching page titles and content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords or natural language query"}
            },
            "required": ["query"]
        },
        "parameters": [
            {"name": "query", "type": "string", "description": "Search keywords or natural language query", "required": True}
        ]
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve the full profile for a customer by their user ID or email address. Returns plan, status, spend, and region.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "Customer user ID"},
                "email": {"type": "string", "description": "Customer email address"}
            }
        },
        "parameters": [
            {"name": "user_id", "type": "integer", "description": "Customer user ID", "required": False},
            {"name": "email", "type": "string", "description": "Customer email address", "required": False}
        ]
    },
    {
        "name": "get_billing_summary",
        "description": "Get billing summary including outstanding invoices, payment history, and current balance for a given user ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "Customer user ID"}
            },
            "required": ["user_id"]
        },
        "parameters": [
            {"name": "user_id", "type": "integer", "description": "Customer user ID", "required": True}
        ]
    },
    {
        "name": "get_support_tickets",
        "description": "Retrieve support tickets for a customer or all open tickets. Filter by status (open, escalated, closed) or priority (low, medium, high, critical).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "Filter by customer user ID (optional)"},
                "status": {"type": "string", "description": "Filter by ticket status (optional)"},
                "priority": {"type": "string", "description": "Filter by priority level (optional)"}
            }
        },
        "parameters": [
            {"name": "user_id", "type": "integer", "description": "Filter by customer user ID", "required": False},
            {"name": "status", "type": "string", "description": "Filter by ticket status", "required": False},
            {"name": "priority", "type": "string", "description": "Filter by priority level", "required": False}
        ]
    },
]


# ── Tool Implementations ─────────────────────────────────────────────────────

def _handle_sql_query(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate SQL query execution against mock data."""
    query = arguments.get("query", "").lower()

    # Route based on query content
    if "invoice" in query or "billing" in query or "unpaid" in query or "overdue" in query:
        if "overdue" in query or "unpaid" in query:
            results = [inv for inv in MOCK_INVOICES if inv["status"] == "overdue"]
        elif "pending" in query:
            results = [inv for inv in MOCK_INVOICES if inv["status"] == "pending"]
        else:
            results = MOCK_INVOICES
    elif "ticket" in query or "support" in query:
        if "open" in query or "escalated" in query:
            results = [t for t in MOCK_TICKETS if t["status"] in ("open", "escalated")]
        elif "critical" in query or "high" in query:
            results = [t for t in MOCK_TICKETS if t["priority"] in ("critical", "high")]
        else:
            results = MOCK_TICKETS
    elif "user" in query or "customer" in query:
        if "churned" in query:
            results = [u for u in MOCK_USERS if u["status"] == "churned"]
        elif "active" in query:
            results = [u for u in MOCK_USERS if u["status"] == "active"]
        elif "suspended" in query:
            results = [u for u in MOCK_USERS if u["status"] == "suspended"]
        elif "enterprise" in query:
            results = [u for u in MOCK_USERS if u["plan"] == "Enterprise"]
        else:
            results = MOCK_USERS
    else:
        results = MOCK_USERS[:3]

    return {
        "content": [{"type": "text", "text": json.dumps({
            "query_executed": arguments.get("query", ""),
            "row_count": len(results),
            "results": results
        }, indent=2)}],
        "isError": False
    }


def _handle_notion_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search mock Notion knowledge base."""
    query = arguments.get("query", "").lower()
    matches = []
    for page in MOCK_NOTION_PAGES:
        if any(word in page["title"].lower() or word in page["content"].lower()
               for word in query.split()):
            matches.append({
                "page_id": page["page_id"],
                "title": page["title"],
                "excerpt": page["content"][:300]
            })

    if not matches:
        matches = [{"page_id": MOCK_NOTION_PAGES[0]["page_id"],
                     "title": MOCK_NOTION_PAGES[0]["title"],
                     "excerpt": MOCK_NOTION_PAGES[0]["content"][:300],
                     "note": "No exact match — returning closest result."}]

    return {
        "content": [{"type": "text", "text": json.dumps({
            "search_query": arguments.get("query", ""),
            "results_found": len(matches),
            "pages": matches
        }, indent=2)}],
        "isError": False
    }


def _handle_get_user_profile(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Lookup a user by ID or email."""
    user_id = arguments.get("user_id")
    email = arguments.get("email", "").lower()

    user = None
    for u in MOCK_USERS:
        if (user_id and u["id"] == user_id) or (email and u["email"].lower() == email):
            user = u
            break

    if not user:
        return {
            "content": [{"type": "text", "text": json.dumps({
                "error": "User not found",
                "searched_by": {"user_id": user_id, "email": email}
            })}],
            "isError": True
        }

    return {
        "content": [{"type": "text", "text": json.dumps(user, indent=2)}],
        "isError": False
    }


def _handle_get_billing_summary(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get billing summary for a user."""
    user_id = arguments.get("user_id")
    user_invoices = [inv for inv in MOCK_INVOICES if inv["user_id"] == user_id]
    user = next((u for u in MOCK_USERS if u["id"] == user_id), None)

    if not user:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": f"User {user_id} not found"})}],
            "isError": True
        }

    total_outstanding = sum(inv["amount"] for inv in user_invoices if inv["status"] in ("pending", "overdue"))
    total_paid = sum(inv["amount"] for inv in user_invoices if inv["status"] == "paid")

    return {
        "content": [{"type": "text", "text": json.dumps({
            "user_id": user_id,
            "customer_name": user["name"],
            "plan": user["plan"],
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "invoices": user_invoices
        }, indent=2)}],
        "isError": False
    }


def _handle_get_support_tickets(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get support tickets with optional filters."""
    user_id = arguments.get("user_id")
    status_filter = arguments.get("status", "").lower()
    priority_filter = arguments.get("priority", "").lower()

    results = MOCK_TICKETS
    if user_id:
        results = [t for t in results if t["user_id"] == user_id]
    if status_filter:
        results = [t for t in results if t["status"] == status_filter]
    if priority_filter:
        results = [t for t in results if t["priority"] == priority_filter]

    return {
        "content": [{"type": "text", "text": json.dumps({
            "filters_applied": {k: v for k, v in arguments.items() if v},
            "ticket_count": len(results),
            "tickets": results
        }, indent=2)}],
        "isError": False
    }


TOOL_HANDLERS = {
    "sql_query": _handle_sql_query,
    "notion_search": _handle_notion_search,
    "get_user_profile": _handle_get_user_profile,
    "get_billing_summary": _handle_get_billing_summary,
    "get_support_tickets": _handle_get_support_tickets,
}


# ── FastAPI JSON-RPC Server ──────────────────────────────────────────────────

mock_app = FastAPI(title="InsightDesk AI — Mock MCP Server", version="1.0.0")


@mock_app.post("/")
async def jsonrpc_handler(request: Request):
    """
    Handle JSON-RPC 2.0 requests per the MCP specification.
    Supports: initialize, tools/list, tools/call, resources/read
    """
    body = await request.json()
    method = body.get("method", "")
    req_id = body.get("id", 1)
    params = body.get("params", {})

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {
                    "name": "InsightDesk-Enterprise-Data",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False}
                }
            }
        })

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        })

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)

        if not handler:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True
                }
            })

        result = handler(arguments)
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

    elif method == "resources/read":
        uri = params.get("uri", "")
        # Match Notion pages by URI
        for page in MOCK_NOTION_PAGES:
            if page["page_id"] in uri or page["title"].lower().replace(" ", "-") in uri.lower():
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": page["content"]
                        }]
                    }
                })
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"contents": [{"uri": uri, "mimeType": "text/plain", "text": "Resource not found."}]}
        })

    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })


@mock_app.get("/health")
async def health():
    return {"status": "healthy", "server": "mock-mcp", "tools": len(TOOLS)}


# ── Standalone Entry Point ───────────────────────────────────────────────────

def start_mock_server(port: int = 8100):
    """Start the mock MCP server (used when running as a subprocess)."""
    import uvicorn
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s │ %(name)-40s │ %(levelname)-7s │ %(message)s",
                        datefmt="%H:%M:%S")
    logger.info("Mock MCP Server starting on port %d with %d tools", port, len(TOOLS))
    uvicorn.run(mock_app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    port = int(os.getenv("MCP_MOCK_PORT", "8100"))
    start_mock_server(port)
