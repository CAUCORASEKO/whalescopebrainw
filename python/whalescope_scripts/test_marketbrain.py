#!/usr/bin/env python3
"""
Test script for MarketBrain API
Checks both live and research modes from backend_ultra_pro.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5001/api/marketbrain"

def test_request(params, label):
    print(f"\n🔎 Testing {label} → {BASE_URL} with params {params}")
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        print("Status Code:", resp.status_code)

        if resp.status_code != 200:
            print("❌ Error response:", resp.text[:200])
            return

        try:
            data = resp.json()
            print("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print("❌ JSON parse error:", e)
            print("Raw response:", resp.text[:200])
            return

        results = data.get("results", [])
        print(f"📊 {len(results)} records received")

        # Show first 3 rows for quick validation
        for row in results[:3]:
            print("   -", {k: row[k] for k in list(row.keys())[:5]})

    except Exception as e:
        print("❌ Request failed:", str(e))


if __name__ == "__main__":
    # Live mode (Allium)
    test_request(
        {"symbols": "solana,ethereum,polygon", "range": "1M", "mode": "live"},
        "LIVE MODE"
    )

    # Research mode (SQLite)
    test_request(
        {"symbols": "solana,ethereum", "range": "3M", "mode": "research"},
        "RESEARCH MODE"
    )