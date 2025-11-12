#!/usr/bin/env python3
# ============================================================
# WhaleScope ETH Data Fetcher (with Staking + AI Insights Pro)
# ------------------------------------------------------------
# - Binance + CoinGecko + Allium + Whale Detector
# - Reads config.json for API keys (no interactive prompts)
# - Outputs ONLY JSON on stdout (for Electron integration)
# - Provides market stats, staking, whale activity,
#   price history, fees, and AI trading insights
# ethallium.py 
# ============================================================

import sys
import json
import logging
import os
import requests
import time
import random
import pandas as pd
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
from appdirs import user_log_dir
from openai import OpenAI

# ============================================================
# CONFIGURATION
# ============================================================
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
CONFIG_FILE = os.path.join(HERE, "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Load error: {e}", file=sys.stderr)
            return {}
    return {}

CFG = load_config()
API_KEY = CFG.get("BINANCE_API_KEY")
API_SECRET = CFG.get("BINANCE_API_SECRET")
COINGECKO_API_KEY = CFG.get("COINGECKO_API_KEY")
ALLIUM_API_KEY = CFG.get("ALLIUM_API_KEY")
OPENAI_API_KEY = CFG.get("OPENAI_API_KEY")

if not API_KEY or not API_SECRET:
    print("⚠️ Binance API keys missing — continuing without authenticated endpoints", file=sys.stderr)
    API_KEY = None
    API_SECRET = None

BINANCE_API_URL = "https://api.binance.com"

ALLIUM_QUERIES = {
    "chain_metrics": "6zhLhumgFL3zQlP1W6B9"
}

# ============================================================
# LOGGING
# ============================================================
log_dir = user_log_dir("WhaleScope", "Cauco")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "eth.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file,
    filemode="a"
)
logger = logging.getLogger(__name__)

# ============================================================
# HELPERS (Caching + Retry Logic)
# ============================================================
CACHE_DIR = "cache"
CACHE_DURATION = 300  # 5 minutes
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_key(key: str):
    return os.path.join(CACHE_DIR, hashlib.md5(key.encode()).hexdigest() + ".json")

def get_cached_response(key: str):
    cache_file = get_cache_key(key)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if time.time() - cached["timestamp"] < CACHE_DURATION:
                return cached["data"]
        except Exception:
            return None
    return None

def cache_response(key: str, data):
    cache_file = get_cache_key(key)
    with open(cache_file, "w") as f:
        json.dump({"timestamp": time.time(), "data": data}, f, indent=2)

def make_request_with_retry(url, headers=None, params=None, max_retries=3):
    cache_key = url + (json.dumps(params, sort_keys=True) if params else "")
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                cache_response(cache_key, data)
                return data
            elif r.status_code == 429:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                return None
        except requests.RequestException as e:
            print(f"[Request error] {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt + random.uniform(0, 1))
    return None

def to_binance_timestamps(start_date, end_date):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    start_ts = int(start_dt.replace(hour=0, minute=0, second=0).timestamp() * 1000)
    end_ts = int(end_dt.replace(hour=23, minute=59, second=59).timestamp() * 1000)
    return start_ts, end_ts

# ============================================================
# COINGECKO
# ============================================================
def fetch_coin_gecko_data():
    url = "https://api.coingecko.com/api/v3/coins/ethereum"
    headers = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
    return make_request_with_retry(url, headers=headers)

# ============================================================
# ALLIUM (Staking)
# ============================================================

def fetch_allium_staking(start_date=None, end_date=None, limit=1000):
    """Fetch staking/chain metrics from Allium for Ethereum with optional date filtering"""
    if not ALLIUM_API_KEY:
        return None

    session = requests.Session()
    session.headers.update({
        "User-Agent": "WhaleScope/1.0",
        "X-API-KEY": ALLIUM_API_KEY
    })

    query_id = ALLIUM_QUERIES["chain_metrics"]
    url = f"https://api.allium.so/api/v1/explorer/queries/{query_id}/run-async"
    payload = {"parameters": {}, "run_config": {"limit": limit}}

    try:
        resp = session.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"[Allium] Error {resp.status_code}: {resp.text}", file=sys.stderr)
            return None

        data = resp.json()
        run_id = data.get("run_id")
        if not run_id:
            print(f"[Allium] Missing run_id: {data}", file=sys.stderr)
            return None

        # Poll until query completes
        status_url = f"https://api.allium.so/api/v1/explorer/query-runs/{run_id}"
        for _ in range(30):
            status = session.get(status_url).json()
            if status.get("status") == "success":
                break
            elif status.get("status") in ("failed", "canceled"):
                print(f"[Allium] Query failed: {status}", file=sys.stderr)
                return None
            time.sleep(1)
        else:
            print("[Allium] Query timeout", file=sys.stderr)
            return None

        # Fetch results
        results_url = f"https://api.allium.so/api/v1/explorer/query-runs/{run_id}/results"
        results = session.get(results_url).json()

        # Parse possible formats
        if "columns" in results and "rows" in results:
            rows = [dict(zip(results["columns"], r)) for r in results["rows"]]
        elif "data" in results:
            rows = results["data"]
        elif isinstance(results, list):
            rows = results
        else:
            rows = []

        # Filter only Ethereum
        eth_rows = [r for r in rows if str(r.get("chain", "")).lower() == "ethereum"]

        # Normalize + Deduplicate
        seen, unique = set(), []
        for row in eth_rows:
            try:
                date_val = row.get("activity_date")
                if date_val and "T" in date_val:  # strip time if needed
                    date_val = date_val.split("T")[0]

                norm = {
                    "activity_date": date_val,
                    "chain": "ethereum",
                    "active_addresses": int(float(row.get("active_addresses", 0))),
                    "total_transactions": int(float(row.get("total_transactions", 0))),
                    "transaction_fees_usd": float(row.get("transaction_fees_usd", 0))
                }

                key = (norm["chain"], norm["activity_date"])
                if key not in seen:
                    seen.add(key)
                    unique.append(norm)
            except Exception as e:
                print(f"[Allium] Normalization error: {e} row={row}", file=sys.stderr)

        # Apply date filtering
        if start_date or end_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
                ed = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
                filtered = []
                for row in unique:
                    if not row.get("activity_date"):
                        continue
                    d = datetime.strptime(row["activity_date"], "%Y-%m-%d")
                    if (not sd or d >= sd) and (not ed or d <= ed):
                        filtered.append(row)
                unique = filtered
            except Exception as e:
                print(f"[Allium] Date filtering error: {e}", file=sys.stderr)

        return unique

    except Exception as e:
        print(f"[Allium] Exception: {e}", file=sys.stderr)
        return None
    
    # ============================================================
# OPENAI INSIGHTS (Basic Fallback)
# ============================================================
def generate_insights(context: dict):
    """Simple fallback insight generator if GPT Pro fails"""
    return {
        "insight": f"Basic analysis: ETH price ${context.get('price')} "
                   f"(24h {context.get('24h_change')}%, "
                   f"7d {context.get('7d_change')}%, "
                   f"30d {context.get('30d_change')}%).",
        "source": "local"
    }

# ============================================================
# OPENAI INSIGHTS (Pro Research Report)
# ============================================================
def get_gpt_insights(staking_rows, context: dict, model="gpt-4o-mini"):
    if not OPENAI_API_KEY:
        return {"insight": "⚠️ No OpenAI API key available", "source": "local"}

    if not staking_rows or not isinstance(staking_rows, list):
        return {"insight": "⚠️ No staking insights available", "source": "local"}

    df = pd.DataFrame(staking_rows)
    text = df.tail(30).to_markdown(index=False)

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""
You are a senior blockchain analyst. Use reliable sources like Ethereum beaconcha.in, Allium metrics, and industry reports.
Analyze Ethereum market and staking data (snapshot: {datetime.now(timezone.utc).strftime('%B %d, %Y')}).
Provide a professional report with:

1. **Current Market Overview**
2. **Staking Data Insights**
   - Active Addresses
   - Transactions
   - Fees
   - Validators / Total ETH Staked
3. **Trends & Institutional Flows**
4. **Risks & Opportunities**
5. **Key Takeaways**

Here is the recent data sample:
{text}

Market context:
{json.dumps(context, indent=2)}

Write the report in Markdown, concise but professional.
"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.6,
        )
        return {"insight": resp.choices[0].message.content.strip(), "source": "OpenAI"}
    except Exception as e:
        return {"insight": f"⚠️ OpenAI error: {e}", "source": "OpenAI"}

# ============================================================
# WHALE DETECTOR
# ============================================================
def detector_actividad_ballenas(data: pd.DataFrame, volume_threshold: float = 2.0, lookback_period: int = 20):
    if data.empty:
        return pd.Series([False] * len(data), index=data.index)
    buy_volume = data["volume"] * (data["close"] > data["open"]).astype(int)
    avg_buy_volume = buy_volume.rolling(window=lookback_period).mean()
    return buy_volume > (avg_buy_volume * volume_threshold)

# ============================================================
# Session cache (only lives while the app is open)
# ============================================================
analysis_cache = {}

def get_cached_analysis(key):
    return analysis_cache.get(key)

def set_cached_analysis(key, value):
    analysis_cache[key] = value

# ============================================================
# CORE FUNCTION (with session cache)
# ============================================================
def fetch_eth_data(start_date=None, end_date=None):
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    # --- Cache key ---
    cache_key = f"eth:{start_date}:{end_date}"
    cached = get_cached_analysis(cache_key)
    if cached:
        print(f"[CACHE] Loaded analysis for {cache_key}", file=sys.stderr)
        return cached

    start_ts, end_ts = to_binance_timestamps(start_date, end_date)

    # --- OHLCV ---
    url_klines = f"{BINANCE_API_URL}/api/v3/klines"
    params = {"symbol": "ETHUSDT", "interval": "1d", "startTime": start_ts, "endTime": end_ts, "limit": 1000}
    historical_data = make_request_with_retry(url_klines, params=params) or []
    price_history = {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    for entry in historical_data:
        date = datetime.utcfromtimestamp(entry[0] / 1000).strftime("%Y-%m-%d")
        price_history["dates"].append(date)
        price_history["open"].append(float(entry[1]))
        price_history["high"].append(float(entry[2]))
        price_history["low"].append(float(entry[3]))
        price_history["close"].append(float(entry[4]))
        price_history["volume"].append(float(entry[5]))
    df = pd.DataFrame(price_history)

    # --- Spot ---
    url_ticker = f"{BINANCE_API_URL}/api/v3/ticker/24hr"
    spot = make_request_with_retry(url_ticker, params={"symbol": "ETHUSDT"}) or {}
    price = float(spot.get("lastPrice", 0))
    percent_change_24h = float(spot.get("priceChangePercent", 0))
    volume_24h = float(spot.get("volume", 0)) * price

    # --- CoinGecko ---
    gecko = fetch_coin_gecko_data()
    if gecko:
        mkt = gecko.get("market_data", {})
        market_cap = mkt.get("market_cap", {}).get("usd", 0)
        fdv = mkt.get("fully_diluted_valuation", {}).get("usd", 0)
        circulating_supply = mkt.get("circulating_supply", 0)

        max_supply = mkt.get("max_supply")
        if not max_supply:
            max_supply = "Unlimited"
    else:
        circulating_supply = 120_000_000
        max_supply = "Unlimited"
        market_cap = price * circulating_supply
        fdv = market_cap

    # --- Exchange Flows ---
    url_trades = f"{BINANCE_API_URL}/api/v3/aggTrades"
    trades = make_request_with_retry(url_trades, params={"symbol": "ETHUSDT", "limit": 1000}) or []

    inflows, outflows = 0.0, 0.0
    for t in trades:
        usd_val = float(t["p"]) * float(t["q"])  # price * quantity
        if t["m"]:
            outflows += usd_val
        else:
            inflows += usd_val

    # Convert from USD to ETH for consistency with BTC
    inflows = inflows / price if price > 0 else 0
    outflows = outflows / price if price > 0 else 0
    net_flow = inflows - outflows

    # --- Whale Detection ---
    top_flows = []
    if not df.empty:
        whale_signals = detector_actividad_ballenas(df)
        for _, row in df[whale_signals].iterrows():
            top_flows.append({
                "timestamp": row["dates"],
                "input_usd": row["volume"] * row["close"],
                "output_usd": 0,
                "status": "whale_buy"
            })
    if not top_flows:
        top_flows = [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_usd": 0, "output_usd": 0, "status": "no_activity"
        }]

    # --- Fees Estimate ---
    fees = {"dates": price_history["dates"], "values": [v * 0.0001 for v in price_history["volume"]]}

    # --- Performance ---
    percent_change_7d = (df["close"].iloc[-1] - df["close"].iloc[-7]) / df["close"].iloc[-7] * 100 if len(df) >= 7 else 0
    percent_change_30d = (df["close"].iloc[-1] - df["close"].iloc[-30]) / df["close"].iloc[-30] * 100 if len(df) >= 30 else 0
    whale_tx = top_flows[0]["input_usd"]

    # --- Staking (Allium) ---
    staking_data = fetch_allium_staking()

    # --- Insights (Pro → fallback Basic) ---
    insights_mode = "basic"
    try:
        insights = get_gpt_insights(
            staking_data,
            {
                "price": price,
                "24h_change": percent_change_24h,
                "7d_change": percent_change_7d,
                "30d_change": percent_change_30d,
                "net_flow": net_flow,
                "whale_tx": whale_tx,
                "date_range": {"start": start_date, "end": end_date}
            }
        )
        if insights and "insight" in insights and not insights.get("insight", "").startswith("⚠️"):
            insights_mode = "pro"
        else:
            insights = generate_insights({
                "price": price,
                "24h_change": percent_change_24h,
                "7d_change": percent_change_7d,
                "30d_change": percent_change_30d
            })
            insights_mode = "basic"
    except Exception:
        insights = generate_insights({
            "price": price,
            "24h_change": percent_change_24h,
            "7d_change": percent_change_7d,
            "30d_change": percent_change_30d
        })
        insights_mode = "basic"

    # --- Final result ---
    result = {
        "type": "result",
        "markets": {
            "price": price,
            "volume_24h": volume_24h,
            "market_cap": market_cap,
            "fdv": fdv,
            "current_supply": circulating_supply,
            "max_supply": max_supply,
            "percent_change_24h": percent_change_24h,
        },
        "yields": {
            "percent_change_24h": percent_change_24h,
            "percent_change_7d": percent_change_7d,
            "percent_change_30d": percent_change_30d,
        },
        "inflows": inflows,
        "outflows": outflows,
        "net_flow": net_flow,
        "top_flows": top_flows,
        "fees": fees,
        "price_history": price_history,
        "staking": staking_data,
        "insights": insights,
        "insights_mode": insights_mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # --- Save to session cache ---
    set_cached_analysis(cache_key, result)
    print(f"[CACHE] Stored analysis for {cache_key}", file=sys.stderr)

    return result

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETH data fetcher")
    parser.add_argument("--start-date", type=str)
    parser.add_argument("--end-date", type=str)
    args = parser.parse_args()

    try:
        data = fetch_eth_data(args.start_date, args.end_date)
        sys.stdout.write(json.dumps(data))
        sys.stdout.flush()
    except Exception as e:
        print(f"[Fatal error] {e}", file=sys.stderr)
        sys.exit(1)