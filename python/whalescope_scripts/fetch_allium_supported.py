#!/usr/bin/env python3
"""
fetch_allium_supported.py
--------------------------------
Tests which symbols are supported by Allium using the same base query (metrics.staking_overview).
"""

import os
import json
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALLIUM_API_KEY")
QUERY_ID = os.getenv("ALLIUM_QUERY_ID", "AcUpz2e1YbQtkOkM1BHG")  # ETH base query
BASE_URL = "https://api.allium.so/api/v1/explorer"
HEADERS = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# Lista inicial (puedes ampliarla)
SYMBOLS = [
    "ETH", "SOL", "MATIC", "BNB", "NEAR", "SUI", "TON", "APTOS",
    "AVAX", "DOT", "FTM", "ADA", "LUNA", "LUNC", "TRX", "XTZ",
    "CRO", "ATOM", "EGLD", "CELO", "FLOW"
]

results = []

def test_symbol(symbol):
    """Run an async command for the symbol and check for data."""
    payload = {
        "parameters": {
            "symbol": symbol,
            "start_date": "2025-09-09",
            "end_date": "2025-10-09"
        },
        "run_config": {"limit": 1000}
    }

    print(f"\n🔍 Testing {symbol} ...")
    try:
        # 1️⃣ Crear run
        run_url = f"{BASE_URL}/queries/{QUERY_ID}/run-async"
        run_resp = requests.post(run_url, headers=HEADERS, json=payload, timeout=60)
        if run_resp.status_code not in (200, 202):
            print(f"❌ {symbol} → {run_resp.status_code}")
            return {"symbol": symbol, "status": "error", "rows": 0}

        run_json = run_resp.json()
        run_id = run_json.get("id") or run_json.get("run_id")
        if not run_id:
            print(f"❌ {symbol} → No run_id")
            return {"symbol": symbol, "status": "error", "rows": 0}

        # 2️⃣ Polling
        poll_url = f"{BASE_URL}/query-runs/{run_id}"
        for i in range(15):
            poll_resp = requests.get(poll_url, headers=HEADERS, timeout=30)
            poll_data = poll_resp.json()
            status = poll_data.get("status", "").lower()
            if status in ("completed", "success", "done", "finished"):
                break
            elif status in ("failed", "error"):
                print(f"❌ {symbol} → Query failed")
                return {"symbol": symbol, "status": "failed", "rows": 0}
            time.sleep(2)

        # 3️⃣ Obtener resultados
        results_url = f"{poll_url}/results"
        results_resp = requests.get(results_url, headers=HEADERS, timeout=60)
        data = results_resp.json().get("data", [])
        count = len(data)
        status = "✅ OK" if count > 0 else "⚠️ Empty"

        print(f"{status} {symbol}: {count} filas")
        return {"symbol": symbol, "status": status, "rows": count}

    except Exception as e:
        print(f"❌ {symbol} → {e}")
        return {"symbol": symbol, "status": "error", "rows": 0}


def main():
    if not API_KEY:
        print("❌ALLIUM_API_KEY is missing from the environment")
        return

    print(f"🚀 Probando {len(SYMBOLS)} symbols with query_id {QUERY_ID}\n")
    for sym in SYMBOLS:
        res = test_symbol(sym)
        results.append(res)

    df = pd.DataFrame(results)
    df.to_csv("allium_supported.csv", index=False)
    print("\n✅ Results saved in allium_supported.csv")
    print(df)


if __name__ == "__main__":
    main()