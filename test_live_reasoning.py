import httpx
import json
import asyncio
import time

CORE_URL = "http://localhost:8000"
INFRA_URL = "http://localhost:8001"

async def test_live_reasoning():
    print("=" * 60)
    print(" InsightDesk AI — Full Stack Integration Test")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # ───────────────────────────────────────────────
        # TEST 1: Health Checks
        # ───────────────────────────────────────────────
        print("\n[TEST 1] Service Health Checks")
        try:
            core_h = await client.get(f"{CORE_URL}/health")
            core_h.raise_for_status()
            ch = core_h.json()
            print(f"  ✓ Core Intelligence: {ch.get('status')} — MCP tools: {ch.get('mcp_tools_available')}")
        except Exception as e:
            print(f"  ✗ Core Intelligence: {e}")
            return

        try:
            infra_h = await client.get(f"{INFRA_URL}/health")
            infra_h.raise_for_status()
            ih = infra_h.json()
            print(f"  ✓ Platform Infra: {ih.get('status')} — SLA targets: {ih.get('sla_targets')}")
        except Exception as e:
            print(f"  ✗ Platform Infra: {e}")
            return

        # ───────────────────────────────────────────────
        # TEST 2: MCP Tool Discovery
        # ───────────────────────────────────────────────
        print("\n[TEST 2] MCP Tool Discovery")
        try:
            tools_resp = await client.get(f"{CORE_URL}/reasoning/tools")
            tools_resp.raise_for_status()
            tools = tools_resp.json()
            print(f"  ✓ Available tools: {tools.get('tools')}")
        except Exception as e:
            print(f"  ✗ Tool discovery failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 3: AI Reasoning Pipeline
        # ───────────────────────────────────────────────
        query = "Look up the current subscription status for account 123 in the database."
        print(f"\n[TEST 3] AI Reasoning Pipeline")
        print(f"  Query: '{query}'")

        t0 = time.time()
        try:
            response = await client.post(f"{CORE_URL}/reasoning/resolve", json={"query": query})
            response.raise_for_status()
            state = response.json()
            latency = time.time() - t0

            print(f"  ✓ Resolved in {latency:.2f}s")
            print(f"    Memory Tier: {state.get('memory_tier_used')}")
            print(f"    Accuracy: {state.get('accuracy_score')}")
            print(f"    Hallucination: {state.get('hallucination_flag')}")
            print(f"    Autonomous: {state.get('autonomous_resolution')}")
            print(f"    Total Latency: {state.get('total_latency_ms')}ms")
            print(f"    Generator: {state.get('generator_provider')}/{state.get('generator_model')}")
            print(f"    Final: {(state.get('final_resolution') or '')[:120]}")

            # Print reasoning trace
            print(f"\n  Reasoning Trace ({len(state.get('steps', []))} steps):")
            for step in state.get("steps", []):
                print(f"    Step {step.get('step_index')}: [{step.get('action_type')}] conf={step.get('confidence')}")
                thinking = step.get("thinking", "")
                print(f"      → {thinking[:100]}{'...' if len(thinking) > 100 else ''}")

            print(f"\n  Tool Calls ({len(state.get('tool_calls', []))}):")
            for tc in state.get("tool_calls", []):
                status = "✓" if tc.get("success") else "✗"
                print(f"    {status} {tc.get('tool_name')} ({tc.get('latency_ms')}ms)")

            session_id = state.get("session_id")
        except Exception as e:
            print(f"  ✗ Reasoning failed: {e}")
            return

        # ───────────────────────────────────────────────
        # TEST 4: Interaction Ingestion
        # ───────────────────────────────────────────────
        print(f"\n[TEST 4] Interaction Ingestion → Platform Infra")
        try:
            ingest_resp = await client.post(f"{INFRA_URL}/interactions/ingest", json=state)
            ingest_resp.raise_for_status()
            print(f"  ✓ Session {session_id} saved to interaction repository")
        except Exception as e:
            print(f"  ✗ Ingestion failed: {e}")
            return

        # ───────────────────────────────────────────────
        # TEST 5: Retrieve Interaction
        # ───────────────────────────────────────────────
        print(f"\n[TEST 5] Interaction Retrieval")
        try:
            detail_resp = await client.get(f"{INFRA_URL}/interactions/{session_id}")
            detail_resp.raise_for_status()
            detail = detail_resp.json()
            interaction = detail.get("interaction", {})
            print(f"  ✓ Retrieved — accuracy={interaction.get('accuracy_score')}, latency={interaction.get('total_latency_ms')}ms")
        except Exception as e:
            print(f"  ✗ Retrieval failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 6: Dashboard Metrics
        # ───────────────────────────────────────────────
        print(f"\n[TEST 6] Dashboard Metrics")
        try:
            metrics_resp = await client.get(f"{INFRA_URL}/metrics/dashboard?window_hours=24")
            metrics_resp.raise_for_status()
            m = metrics_resp.json()
            print(f"  ✓ Total Interactions: {m.get('total_interactions')}")
            print(f"    Avg Accuracy: {m.get('avg_accuracy')}")
            print(f"    Avg Latency: {m.get('avg_latency_ms')}ms")
            print(f"    Resolution Rate: {m.get('resolution_rate')}")
            print(f"    Hallucination Rate: {m.get('hallucination_rate')}")
        except Exception as e:
            print(f"  ✗ Metrics failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 7: DAG Validation
        # ───────────────────────────────────────────────
        print(f"\n[TEST 7] DAG Path Validation")
        try:
            dags_resp = await client.get(f"{INFRA_URL}/metrics/dags")
            dags_resp.raise_for_status()
            dags = dags_resp.json()
            print(f"  ✓ Available DAGs: {dags.get('dags')}")
        except Exception as e:
            print(f"  ✗ DAG list failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 8: RCA Diagnostics
        # ───────────────────────────────────────────────
        print(f"\n[TEST 8] RCA Diagnostics")
        try:
            rca_resp = await client.post(f"{INFRA_URL}/diagnostics/analyze", json={"session_id": session_id})
            rca_resp.raise_for_status()
            rca = rca_resp.json()
            print(f"  ✓ RCA Analysis complete")
            print(f"    Category: {rca.get('failure_category', 'N/A')}")
            print(f"    Severity: {rca.get('severity', 'N/A')}")
        except Exception as e:
            print(f"  ✗ RCA failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 9: Self-Healing Stats
        # ───────────────────────────────────────────────
        print(f"\n[TEST 9] Self-Healing Stats")
        try:
            heal_resp = await client.get(f"{CORE_URL}/healing/stats")
            heal_resp.raise_for_status()
            hs = heal_resp.json()
            print(f"  ✓ Total Healing Runs: {hs.get('total_healing_runs')}")
            print(f"    Maintenance Reduction: {hs.get('maintenance_reduction_pct')}%")
            print(f"    Registered Journeys: {hs.get('registered_journeys')}")
        except Exception as e:
            print(f"  ✗ Healing stats failed: {e}")

        # ───────────────────────────────────────────────
        # TEST 10: JRH 3-Judge Evaluation (longer timeout)
        # ───────────────────────────────────────────────
        print(f"\n[TEST 10] JRH 3-Judge Ensemble Evaluation")
        print(f"  (Calling 3 external AI providers — this may take 30-90s...)")
        try:
            jrh_resp = await client.post(f"{INFRA_URL}/evaluate/jrh", json={"session_id": session_id})
            jrh_resp.raise_for_status()
            jrh = jrh_resp.json()
            print(f"  ✓ JRH Complete!")
            print(f"    Composite Score: {jrh.get('composite_score')}/10.0")
            print(f"    Needs Human Calibration: {jrh.get('needs_human_calibration')}")
            for s in jrh.get("judge_scores", []):
                print(f"    Judge [{s.get('provider')}]: {s.get('score')}/10 (conf={s.get('confidence')})")
        except httpx.ReadTimeout:
            print(f"  ⚠ JRH timed out (external AI providers slow) — this is expected on cold starts")
        except Exception as e:
            print(f"  ✗ JRH failed: {e}")

    # ───────────────────────────────────────────────
    # SUMMARY
    # ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" Integration Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_live_reasoning())
