"""Quick integration test for all platform-infra endpoints."""
import httpx
import json
import uuid

BASE = "http://localhost:8200"

def test():
    # Use dynamic session IDs to avoid UniqueConstraint errors
    session_1 = f"test-session-{uuid.uuid4()}"
    session_bad = f"test-session-bad-{uuid.uuid4()}"

    # Test 1: Health
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    print("[PASS] GET /health")

    # Test 2: Root
    r = httpx.get(f"{BASE}/")
    assert r.status_code == 200
    data = r.json()
    assert "interaction_repository" in data["capabilities"]
    print(f"[PASS] GET / — {len(data['capabilities'])} capabilities")

    # Test 3: Ingest interaction
    payload = {
        "session_id": session_1,
        "query": "What is my current account balance?",
        "steps": [
            {"step_index": 0, "thinking": "Verify account", "action_type": "tool_call",
             "action_input": {"tool": "verify_account"}, "confidence": 0.95},
            {"step_index": 1, "thinking": "Check balance", "action_type": "tool_call",
             "action_input": {"tool": "check_balance"}, "confidence": 0.92},
        ],
        "tool_calls": [
            {"tool_name": "verify_account", "arguments": {"user_id": "123"},
             "success": True, "latency_ms": 45.0},
            {"tool_name": "check_balance", "arguments": {"account_id": "A456"},
             "result": {"balance": 1234.56}, "success": True, "latency_ms": 82.0},
        ],
        "final_resolution": "Your current account balance is $1,234.56.",
        "autonomous_resolution": True,
        "accuracy_score": 0.99,
        "hallucination_flag": False,
        "total_latency_ms": 127.0,
    }
    r = httpx.post(f"{BASE}/interactions/ingest", json=payload)
    assert r.status_code == 200
    print(f"[PASS] POST /interactions/ingest — session={r.json()['session_id']}")

    # Test 4: Ingest a LOW-quality interaction for RCA testing
    bad_payload = {
        "session_id": session_bad,
        "query": "Process my refund for order #789",
        "steps": [
            {"step_index": 0, "thinking": "Look up order", "action_type": "tool_call",
             "action_input": {"tool": "find_order"}, "confidence": 0.3},
        ],
        "tool_calls": [
            {"tool_name": "find_order", "arguments": {"order_id": "789"},
             "success": False, "error": "Order not found", "latency_ms": 850.0},
        ],
        "final_resolution": "I could not find your order.",
        "autonomous_resolution": False,
        "accuracy_score": 0.45,
        "hallucination_flag": True,
        "total_latency_ms": 900.0,
    }
    r = httpx.post(f"{BASE}/interactions/ingest", json=bad_payload)
    assert r.status_code == 200
    print(f"[PASS] POST /interactions/ingest (bad) — session={r.json()['session_id']}")

    # Test 5: List interactions
    r = httpx.get(f"{BASE}/interactions/")
    assert r.status_code == 200
    print(f"[PASS] GET /interactions/ — {len(r.json())} interactions")

    # Test 6: Get single interaction
    r = httpx.get(f"{BASE}/interactions/{session_1}")
    assert r.status_code == 200
    print(f"[PASS] GET /interactions/{session_1}")

    # Test 7: JRH evaluation (direct)
    r = httpx.post(f"{BASE}/evaluate/jrh/direct", json={
        "query": "What is my balance?",
        "thought_chain": [{"step_index": 0, "thinking": "check", "action_type": "tool_call", "confidence": 0.9}],
        "final_resolution": "Your balance is $1,234.",
        "tool_calls": [],
    })
    assert r.status_code == 200
    jrh = r.json()
    print(f"[PASS] POST /evaluate/jrh/direct — composite={jrh['composite_score']} entropy={jrh['entropy']}")

    # Test 8: JRH evaluation (stored)
    r = httpx.post(f"{BASE}/evaluate/jrh", json={"session_id": session_1})
    assert r.status_code == 200
    print(f"[PASS] POST /evaluate/jrh — composite={r.json()['composite_score']}")

    # Test 9: G-Eval
    r = httpx.post(f"{BASE}/evaluate/g-eval", json={"session_id": session_1})
    assert r.status_code == 200
    ge = r.json()
    print(f"[PASS] POST /evaluate/g-eval — quality={ge['composite_quality']}")

    # Test 10: Get verdicts
    r = httpx.get(f"{BASE}/evaluate/verdicts/{session_1}")
    assert r.status_code == 200
    print(f"[PASS] GET /evaluate/verdicts — {len(r.json()['verdicts'])} verdicts")

    # Test 11: RCA analysis
    r = httpx.post(f"{BASE}/diagnostics/analyze", json={"session_id": session_bad})
    assert r.status_code == 200
    rca = r.json()
    print(f"[PASS] POST /diagnostics/analyze — category={rca['primary_category']} severity={rca['primary_severity']}")

    # Test 12: List RCA traces
    r = httpx.get(f"{BASE}/diagnostics/traces")
    assert r.status_code == 200
    print(f"[PASS] GET /diagnostics/traces — {len(r.json())} traces")

    # Test 13: DAG listing
    r = httpx.get(f"{BASE}/metrics/dags")
    assert r.status_code == 200
    print(f"[PASS] GET /metrics/dags — {len(r.json()['dags'])} DAGs")

    # Test 14: DAG validation
    r = httpx.get(f"{BASE}/metrics/dag-validate/{session_1}?dag_name=billing_adjustment")
    assert r.status_code == 200
    dag = r.json()
    print(f"[PASS] GET /metrics/dag-validate — passed={dag['passed']} completeness={dag['path_completeness']}")

    # Test 15: Dashboard metrics
    r = httpx.get(f"{BASE}/metrics/dashboard")
    assert r.status_code == 200
    dash = r.json()
    print(f"[PASS] GET /metrics/dashboard — {dash['total_interactions']} interactions")

    # Test 16: Trends
    r = httpx.get(f"{BASE}/metrics/trends?window_hours=24")
    assert r.status_code == 200
    print(f"[PASS] GET /metrics/trends — {r.json()['data_points']} data points")

    print("\n=== ALL 16 ENDPOINT TESTS PASSED ===")

if __name__ == "__main__":
    test()
