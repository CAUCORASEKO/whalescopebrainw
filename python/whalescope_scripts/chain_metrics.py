#!/usr/bin/env python3
"""
chain_metrics.py
Fetch chain metrics from Allium (via run-async) and optionally add GPT insights.
"""

import os, sys, json, argparse, requests, time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

ALLIUM_KEY = os.getenv("ALLIUM_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

QUERY_ID = "6zhLhumgFL3zQlP1W6B9"

if not ALLIUM_KEY:
    print(json.dumps({
        "type": "marketbrain",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "error": "ALLIUM_API_KEY not configured",
        "source": "Allium"
    }, indent=2))
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "WhaleScope/1.0",
    "X-API-KEY": ALLIUM_KEY
})

# ================== HELPERS ==================
def fetch_query_results(limit):
    """Fetch results from Allium using run-async with a fixed query_id."""
    # 1. Lanzar el query
    url = f"https://api.allium.so/api/v1/developer/queries/{QUERY_ID}/run-async"
    resp = session.post(url, json={"parameters": {}}, timeout=30)
    resp.raise_for_status()
    run = resp.json()
    run_id = run.get("id")
    if not run_id:
        raise RuntimeError(f"No run_id returned from Allium: {run}")

    # 2. Poll to success
    url = f"https://api.allium.so/api/v1/developer/query-results/{run_id}"
    for _ in range(30):  # ~30s max
        r = session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            rows = data.get("data", [])
            return rows[:limit]
        elif data.get("status") in ("failed", "error"):
            raise RuntimeError(f"Query failed: {data}")
        time.sleep(1)

    raise TimeoutError("Query did not finish in time")

def get_gpt_insights(rows):
    """Envia resultados a OpenAI para generar insights"""
    if not OPENAI_KEY:
        return ["[WARN] OPENAI_API_KEY not configured"]

    import openai
    openai.api_key = OPENAI_KEY

    # We've summarized the data a bit to avoid having thousands of rows.
    preview = rows[:50] if len(rows) > 50 else rows
    text_input = f"Analyze blockchain activity data and summarize trends:\n{json.dumps(preview, indent=2)}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a crypto market analyst."},
                {"role": "user", "content": text_input}
            ],
            max_tokens=300
        )
        return [response.choices[0].message["content"]]
    except Exception as e:
        return [f"[GPT error] {str(e)}"]

# ================== MAIN ==================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500,
                        help="Número máximo de filas")
    parser.add_argument("--api", action="store_true",
                        help="Output JSON payload para Electron")
    parser.add_argument("--insights", choices=["gpt"], help="Añadir insights con GPT")
    args = parser.parse_args()

    try:
        rows = fetch_query_results(args.limit)

        payload = {
            "type": "marketbrain",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": rows,
            "chains": sorted(set(r["chain"] for r in rows)) if rows else [],
            "period": f"last {args.limit} rows",
            "analysis": f"Fetched {len(rows)} rows from query {QUERY_ID}",
            "source": "Allium",
            "insights": []
        }

        if args.insights == "gpt" and rows:
            payload["insights"] = get_gpt_insights(rows)

        print(json.dumps(payload if args.api else rows, indent=2, default=str))

    except Exception as e:
        print(json.dumps({
            "type": "marketbrain",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "error": str(e),
            "source": "Allium"
        }, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()