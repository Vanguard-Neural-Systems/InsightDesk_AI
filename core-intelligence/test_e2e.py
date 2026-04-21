"""
InsightDesk AI — End-to-End Self-Healing Test
Registers a journey, simulates UI drift, and triggers autonomous healing.
"""
import httpx
import json

BASE = "http://localhost:8000"

# ── 1. Register a test journey ───────────────────────────────────────────────
journey = {
    "journey_id": "login-flow-001",
    "name": "User Login Flow",
    "description": "Tests the login page end-to-end",
    "steps": [
        {
            "step_index": 0,
            "action": "navigate",
            "target": {
                "element_id": "login-page",
                "element_type": "ui_link",
                "selector": "/login",
                "attributes": {"title": "Login Page"},
            },
        },
        {
            "step_index": 1,
            "action": "type",
            "target": {
                "element_id": "email-input",
                "element_type": "ui_input",
                "selector": "#email-field",
                "attributes": {"placeholder": "Enter email", "type": "email"},
            },
            "input_value": "test@example.com",
        },
        {
            "step_index": 2,
            "action": "click",
            "target": {
                "element_id": "submit-btn",
                "element_type": "ui_button",
                "selector": "button.login-submit",
                "attributes": {"text": "Sign In", "aria-label": "Submit login"},
            },
        },
    ],
    "is_healthy": True,
}

r = httpx.post(f"{BASE}/healing/journeys", json=journey)
print("1. Register journey:", r.json())

# ── 2. Simulate UI drift ────────────────────────────────────────────────────
# The front-end team refactored: selectors changed, button text changed.
current_fingerprints = [
    {
        "element_id": "login-page",
        "element_type": "ui_link",
        "selector": "/login",
        "attributes": {"title": "Login Page"},
    },
    {
        "element_id": "email-input",
        "element_type": "ui_input",
        "selector": "#user-email",               # CHANGED from #email-field
        "attributes": {"placeholder": "Enter email", "type": "email"},
    },
    {
        "element_id": "submit-btn",
        "element_type": "ui_button",
        "selector": "button.btn-primary",         # CHANGED from button.login-submit
        "attributes": {"text": "Log In", "aria-label": "Submit login"},  # text changed
    },
]

r = httpx.post(f"{BASE}/healing/heal", json={
    "journey_id": "login-flow-001",
    "current_fingerprints": current_fingerprints,
})
report = r.json()

print("\n2. Healing Report:")
print(f"   Patches generated: {len(report['patches'])}")
print(f"   Auto-applied:      {report['auto_applied']}")
print(f"   Needs review:      {report['needs_review']}")
print(f"   Journey healed:    {report['journey_healed']}")

for p in report["patches"]:
    print(f"\n   Step {p['step_index']}: {p['drift_type']} (confidence: {p['confidence']:.2f})")
    print(f"   Reasoning: {p['reasoning'][:150]}...")

# ── 3. Check healing stats ───────────────────────────────────────────────────
r = httpx.get(f"{BASE}/healing/stats")
print("\n3. Healing Stats:", r.json())

# ── 4. Verify journey health ─────────────────────────────────────────────────
r = httpx.get(f"{BASE}/healing/journeys")
journeys = r.json()
for j in journeys:
    print(f"\n4. Journey '{j['name']}': healthy={j['is_healthy']}")
