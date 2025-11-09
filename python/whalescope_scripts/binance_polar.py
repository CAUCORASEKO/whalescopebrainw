#!/usr/bin/env python3
# WhaleScope Binance Polar Dashboard
# Generates multi-timeframe dominance & volatility rotation map.

import ccxt
import pandas as pd
import numpy as np
import os
import json
import sys
import time
import logging
import appdirs

# ---------------- CONFIG ----------------


# Load keys from Electron backend storage
CONFIG_PATH = os.path.join(appdirs.user_data_dir("whalescope"), "api_keys.json")

api_key = None
api_secret = None

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            api_key = cfg.get("BINANCE_API_KEY")
            api_secret = cfg.get("BINANCE_API_SECRET")
    except:
        pass

# If keys missing, still continue (use public endpoints)
if not api_key or not api_secret:
    print("⚠️ Binance API keys missing — continuing with public endpoints", file=sys.stderr)
    api_key = None
    api_secret = None

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True
})

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True
})

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------------- SYMBOLS ----------------
tickers = [
    "BTC/USDT", "ETH/USDT", "XRP/USDT", "BNB/USDT", "SOL/USDT",
    "DOGE/USDT", "ADA/USDT", "TRX/USDT", "LINK/USDT", "AVAX/USDT"
]

limit = 365  # 1 year of daily candles

# ---------------- HELPERS ----------------
def fetch_daily_ohlcv(symbol):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=limit)
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df["v_usdt"] = df["volume"] * df["close"]
        df["delta"] = np.abs(df["close"] - df["open"]) / df["open"]
        return df
    except Exception as e:
        logging.error(f"Failed OHLCV {symbol}: {e}")
        return pd.DataFrame()

def aggregate_period(df, period):
    if df.empty:
        return None
    rule = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "ME",
        "yearly": "YE"
    }[period]
    agg = df.resample(rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "v_usdt": "sum",
        "delta": "mean"
    }).dropna()
    return agg

def compute_polar_for_period(symbol, period, df):
    agg = aggregate_period(df, period)
    if agg is None or agg.empty:
        return {
            "symbol": symbol, "cum_vol": 0, "cum_delta": 0, "dominance": 0, "percent": 0
        }
    cum_vol = agg["v_usdt"].sum()
    cum_delta = agg["delta"].mean()
    dominance = cum_vol * cum_delta
    return {
        "symbol": symbol,
        "cum_vol": float(cum_vol),
        "cum_delta": float(cum_delta),
        "dominance": float(dominance)
    }

# ---------------- CORE ----------------
def generate_multi_polar():
    periods = ["daily", "weekly", "monthly", "yearly"]
    all_results = {p: {"timeframe": p, "data": [], "insights": []} for p in periods}

    for symbol in tickers:
        df_daily = fetch_daily_ohlcv(symbol)
        time.sleep(exchange.rateLimit / 1000)

        for p in periods:
            entry = compute_polar_for_period(symbol, p, df_daily)
            all_results[p]["data"].append(entry)

    # compute dominance %, add insights
    for p in periods:
        df_res = pd.DataFrame(all_results[p]["data"])
        total_dom = df_res["dominance"].sum()

        df_res["percent"] = (df_res["dominance"] / total_dom * 100) if total_dom > 0 else 0
        all_results[p]["data"] = df_res.to_dict(orient="records")

        insights = []
        if total_dom > 0 and not df_res.empty:
            leader = df_res.sort_values("percent", ascending=False).iloc[0]
            insights.append(f"{leader['symbol']} leads {p} with {leader['percent']:.2f}% dominance.")
        all_results[p]["insights"] = insights

    return {
        "type": "binance_polar",
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "results": all_results
    }

# ---------------- MAIN ----------------
def main():
    try:
        output = generate_multi_polar()
        print(json.dumps(output, indent=2))
    except Exception as e:
        logging.error(f"Exception: {e}")
        print(json.dumps({"error": f"Failed: {e}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()