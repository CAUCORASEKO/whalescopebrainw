#!/usr/bin/env python3
# ============================================================
# Binance Market → CSV Export
# ------------------------------------------------------------
# Exports:
# - OHLCV
# - Whale Netflow
# - Fundamentals
# - Smart Money phase + Accumulation score
# - Whale Activity Table
# - export_binance_market_csv.py
# ============================================================

import sys
import json
import argparse
import pandas as pd
import os
import requests
from datetime import datetime


def fetch_binance_market(symbol, start, end):
    url = "http://127.0.0.1:5001/api/binance_market"
    params = {"symbol": symbol, "startDate": start, "endDate": end}
    r = requests.get(url, params=params, timeout=25)

    if r.status_code != 200:
        raise RuntimeError(f"API error: {r.status_code} {r.text}")

    data = r.json()
    return data.get("results", {}).get(symbol.upper(), {})


def export_csv(symbol, start, end):
    data = fetch_binance_market(symbol, start, end)
    sym = symbol.upper()

    # === PRICE DATA ===
    candles = data.get("candles", {})
    df_price = pd.DataFrame({
        "date": candles.get("dates", []),
        "open": candles.get("open", []),
        "high": candles.get("high", []),
        "low": candles.get("low", []),
        "close": candles.get("close", []),
        "volume": candles.get("volume", []),
    })

    # === NETFLOW ===
    netflow = data.get("netflow", {})
    df_net = pd.DataFrame({
        "date": netflow.get("dates", []),
        "netflow_usd": netflow.get("values", [])
    })

    # === FUNDAMENTALS ===
    markets = data.get("markets", {})
    df_fund = pd.DataFrame([{
        "symbol": sym,
        "price": markets.get("price"),
        "market_cap": markets.get("market_cap"),
        "fdv": markets.get("fdv"),
        "circulating_supply": markets.get("current_supply"),
        "max_supply": markets.get("max_supply"),
    }])

    # === PERFORMANCE ===
    perf = data.get("performance", {})
    df_perf = pd.DataFrame([perf])

    # === SMART MONEY ===
    df_meta = pd.DataFrame([{
        "symbol": sym,
        "smart_money_phase": data.get("smart_money_phase"),
        "accumulation_score": data.get("accumulation_score")
    }])

    # === WHALE ACTIVITY TABLE ===
    whales = data.get("whales_table", [])
    df_whales = pd.DataFrame(whales)

    # === OUTPUT FILE ===
    out_dir = "/tmp"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"WhaleScope_{sym}_{start}_{end}.csv")

    # === WRITE SECTIONS ===
    with open(out_file, "w") as f:
        f.write("=== Price Data ===\n")
    df_price.to_csv(out_file, index=False, mode="a")

    with open(out_file, "a") as f:
        f.write("\n=== Whale Netflow (USD) ===\n")
    df_net.to_csv(out_file, index=False, mode="a")

    with open(out_file, "a") as f:
        f.write("\n=== Market Fundamentals ===\n")
    df_fund.to_csv(out_file, index=False, mode="a")

    with open(out_file, "a") as f:
        f.write("\n=== Performance ===\n")
    df_perf.to_csv(out_file, index=False, mode="a")

    with open(out_file, "a") as f:
        f.write("\n=== Smart Money Indicators ===\n")
    df_meta.to_csv(out_file, index=False, mode="a")

    with open(out_file, "a") as f:
        f.write("\n=== Whale Activity Table ===\n")
    df_whales.to_csv(out_file, index=False, mode="a")

    print(out_file)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("symbol", type=str)
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    args = p.parse_args()

    export_csv(args.symbol, args.start_date, args.end_date)


if __name__ == "__main__":
    main()