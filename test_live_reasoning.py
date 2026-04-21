import httpx
import json
import asyncio
import time

CORE_URL = "http://localhost:8000"
INFRA_URL = "http://localhost:8200"

async def test_live_reasoning():
    print("==================================================")
    print(" InsightDesk AI — Live E2E Reasoning Test")
    print("==================================================")

    query = "Look up the current subscription status for account 123 in the database."
    print(f"\n[1] Sending Query to Core Intelligence: '{query}'")
    
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Ask the AI
            response = await client.post(f"{CORE_URL}/reasoning/resolve", json={"query": query})
            response.raise_for_status()
            state = response.json()
            
            latency = time.time() - t0
            print(f"[SUCCESS] Core Engine resolved in {latency:.2f}s using {state.get('memory_tier_used')}")
            print(f"   Final Resolution: {state.get('final_resolution')}")
            
            # Print Reasoning Chain
            print("\n[2] Agent Reasoning Trace:")
            for step in state.get("steps", []):
                print(f"   Step {step.get('step_index')}: {step.get('action_type')} (conf: {step.get('confidence')})")
                print(f"     -> {step.get('thinking')}")
            
            session_id = state.get("session_id")
            
            print(f"\n[3] Ingesting to Platform Infrastructure Memory (Session: {session_id})...")
            # 2. Ingest to Platform Infra memory (normally done via background queue)
            ingest_resp = await client.post(f"{INFRA_URL}/interactions/ingest", json=state)
            if ingest_resp.status_code == 200:
                print("[SUCCESS] Successfully saved to interaction repository.")
            else:
                print("[ERROR] Failed to ingest interaction:", ingest_resp.text)
                return

            print("\n[4] Running JRH 3-Judge Ensemble (NVIDIA, Groq, Gemini)...")
            # 3. Run JRH Evaluation
            jrh_resp = await client.post(f"{INFRA_URL}/evaluate/jrh", json={"session_id": session_id})
            if jrh_resp.status_code == 200:
                jrh = jrh_resp.json()
                print(f"[SUCCESS] JRH Complete: Composite Score = {jrh.get('composite_score')}/10.0")
                print(f"   Entropy = {jrh.get('entropy'):.4f} (Needs Human Calibration: {jrh.get('needs_human_calibration')})")
                for s in jrh.get("judge_scores", []):
                    print(f"   - {s.get('provider')}: {s.get('score')}/10 (Latency: {s.get('latency_ms'):.0f}ms)")
            else:
                print("[ERROR] Failed to run JRH:", jrh_resp.text)

    except httpx.ConnectError:
        print("\n[ERROR] Could not connect to the servers.")
        print("   Please ensure that both core-intelligence (port 8000)")
        print("   and platform-infra (port 8200) are running.")

if __name__ == "__main__":
    asyncio.run(test_live_reasoning())
