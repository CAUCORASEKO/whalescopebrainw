#!/usr/bin/env python3
# ============================================================
# WhaleScope ETH Data Fetcher (Allium + Binance + CoinGecko)
# ------------------------------------------------------------
# - Market data (Binance + CoinGecko)
# - Staking & chain activity (Allium)
# - Whale detection
# - Saves staking to SQLite (eth_activity + eth_entities)
# - Outputs ONLY JSON for Electron integration
# ============================================================

import sqlite3
import sys
import json
import logging
import os
import requests
import time
import random
import pandas as pd
import numpy as np

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
# Queries de Allium
ALLIUM_QUERY_ID_ACTIVITY = CFG.get("ALLIUM_QUERY_ID_ACTIVITY", "VavipYXMPM2oXLWR6Bwm")
ALLIUM_QUERY_ID_ENTITIES = CFG.get("ALLIUM_QUERY_ID_ENTITIES")  # optional
ALLIUM_QUERY_ID_STAKERS = CFG.get("ALLIUM_QUERY_ID_STAKERS")    # for deposits/withdrawals
ALLIUM_QUERY_ID = CFG.get("ALLIUM_QUERY_ID")                    # generic fallback



if not API_KEY or not API_SECRET:
    print("⚠️ Binance API keys missing — continuing without authenticated endpoints", file=sys.stderr)
    API_KEY = None
    API_SECRET = None

BINANCE_API_URL = "https://api.binance.com"
# Queries de Allium
ALLIUM_QUERY_ID_ACTIVITY = CFG.get("ALLIUM_QUERY_ID_ACTIVITY", "VavipYXMPM2oXLWR6Bwm")
ALLIUM_QUERY_ID_ENTITIES = CFG.get("ALLIUM_QUERY_ID_ENTITIES")  

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
# HELPERS (cache, retry, timestamps)
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
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                cache_response(cache_key, data)
                return data
            elif r.status_code == 429:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                print(f"[Request error] {r.status_code}: {r.text}", file=sys.stderr)
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
# STAKING: BUILD SNAPSHOT + TIME SERIES
# ============================================================

def build_staking_json(start_date, end_date):
    """Read staking + entities rows from SQLite and build JSON snapshot + timeseries + extra sections"""
    from datetime import datetime
    import sqlite3, os

    # --- Detect date range ---
    d0 = datetime.fromisoformat(start_date)
    d1 = datetime.fromisoformat(end_date)
    delta_days = (d1 - d0).days

    # Choose granularity
    if delta_days <= 90:
        granularity = "day"
        date_expr = "activity_date"
    elif delta_days <= 365:
        granularity = "week"
        date_expr = "strftime('%Y-%W', activity_date)"  # año-semana
    else:
        granularity = "month"
        date_expr = "strftime('%Y-%m', activity_date)"  # año-mes

    db_path = os.path.abspath(os.path.join(HERE, "..", "..", "whalescope.db"))
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        # --- Read activity with resample ---
        cur.execute(f"""
            SELECT {date_expr} as period,
                   SUM(total_stake) as total_stake,
                   SUM(active_stake) as active_stake,
                   AVG(pct_total_stake_active) as pct_total_stake_active,
                   AVG(pct_circulating_staked_est) as pct_circulating_staked_est,
                   SUM(COALESCE(daily_net_stake,0)) as daily_net_stake,
                   SUM(COALESCE(deposits_est_eth,0)) as deposits,
                   SUM(COALESCE(withdrawals_est_eth,0)) as withdrawals
            FROM eth_activity
            WHERE activity_date BETWEEN ? AND ?
            GROUP BY period
            ORDER BY period ASC
        """, (start_date, end_date))
        rows = cur.fetchall()

        # --- Entities (all records within the range) ---
        cur.execute("""
            SELECT activity_date, entity, staked, share
            FROM eth_entities
            WHERE activity_date BETWEEN ? AND ?
            ORDER BY activity_date ASC
        """, (start_date, end_date))
        entity_rows = cur.fetchall()

    if not rows:
        return {}

    # === Activity ===
    dates = [r[0] for r in rows]
    total_stake = [r[1] for r in rows]
    active_stake = [r[2] for r in rows]
    pct_active = [r[3] for r in rows]
    pct_circ_staked = [r[4] for r in rows]
    daily_net = [r[5] for r in rows]
    deposits = [r[6] for r in rows]
    withdrawals = [r[7] for r in rows]

    snapshot = {
        "activity_date": dates[-1],
        "total_stake": total_stake[-1],
        "active_stake": active_stake[-1],
        "pct_total_stake_active": pct_active[-1],
        "pct_circulating_staked_est": pct_circ_staked[-1],
    }

    timeseries = {
        "dates": dates,
        "total_stake": total_stake,
        "active_stake": active_stake,
        "pct_total_stake_active": pct_active,
        "pct_circulating_staked": pct_circ_staked,
        "daily_net_stake": daily_net,
        "deposits_est_eth": deposits,
        "withdrawals_est_eth": withdrawals,
        "granularity": granularity,   # 👈 important for frontend
    }

    # === Entities (most recent snapshot only) ===
    entities = [
        {
            "activity_date": er[0],
            "entity": er[1],
            "staked": float(er[2]) if er[2] is not None else 0.0,
            "share": float(er[3]) if er[3] is not None else None,
        }
        for er in entity_rows
    ]

    breakdown_labels, breakdown_values = [], []
    entity_dates = []
    if entities:
        entity_dates = sorted({e["activity_date"] for e in entities})
        latest_entities_date = entity_dates[-1]

        # Only most recent snapshot
        filtered = [e for e in entities if e["activity_date"] == latest_entities_date]

        # Sort by stake and limit Top-10
        sorted_entities = sorted(
            [(e["entity"], float(e["staked"] or 0.0)) for e in filtered],
            key=lambda x: x[1],
            reverse=True
        )

        top_entities = sorted_entities[:10]
        others_sum = sum(val for _, val in sorted_entities[10:])

        breakdown_labels = [lbl for lbl, _ in top_entities]
        breakdown_values = [val for _, val in top_entities]

        if others_sum > 0:
            breakdown_labels.append("Others")
            breakdown_values.append(others_sum)

    # === Market Share (only last 30 dates to avoid JSON overload) ===
    marketshare = {"dates": entity_dates[-30:], "series": []}
    if entities and entity_dates:
        totals_by_date = {}
        for e in entities:
            d = e["activity_date"]
            totals_by_date[d] = totals_by_date.get(d, 0.0) + float(e["staked"] or 0.0)

        series_map = {}
        for e in entities:
            name = e["entity"]
            if name not in series_map:
                series_map[name] = {d: 0.0 for d in entity_dates[-30:]}
            if e["activity_date"] in series_map[name]:
                total = totals_by_date.get(e["activity_date"], 0.0)
                pct = (float(e.get("staked") or 0.0) / total * 100.0) if total > 0 else 0.0
                series_map[name][e["activity_date"]] = pct

        marketshare["series"] = [
            {"name": name, "values": [series_map[name][d] for d in entity_dates[-30:]]}
            for name in series_map
        ]

    # === Categorization ===
    CATEGORY_MAP = {
        "Liquid Staking Participants": ["lido", "rocket"],
        "CEX Participants": ["binance", "coinbase", "kraken", "okx", "huobi"],
        "Restaking Participants": ["eigen"],
        "Staking Pools Participants": []
    }

    def categorize_entity(entity_name: str) -> str:
        name = (entity_name or "").lower()
        for category, keywords in CATEGORY_MAP.items():
            if any(kw in name for kw in keywords):
                return category
        return "Staking Pools Participants"

    breakdown_by_category = {}
    if entities:
        latest_entities = [e for e in entities if e["activity_date"] == entity_dates[-1]]
        for e in latest_entities:
            cat = categorize_entity(e["entity"])
            breakdown_by_category[cat] = breakdown_by_category.get(cat, 0.0) + (e["staked"] or 0.0)
        for cat in CATEGORY_MAP.keys():
            breakdown_by_category.setdefault(cat, 0.0)

    # === Recent Events (last 10 periods) ===
    recent_events = []
    for d, dep, wdr in zip(dates[-10:], deposits[-10:], withdrawals[-10:]):
        recent_events.append({"date": d, "staked": float(dep or 0.0), "unstaked": float(wdr or 0.0)})

    return {
        "latest": snapshot,
        "series": timeseries,
        "staking_flows": {"dates": dates, "inflows": deposits, "outflows": withdrawals},
        "stakers_change": {"dates": dates, "values": daily_net},
        "entities": entities,
        "deposits": {"dates": dates, "values": deposits},
        "withdrawals": {"dates": dates, "values": withdrawals},
        "staked_over_time": {"dates": dates, "values": total_stake},
        "staked_breakdown": {"labels": breakdown_labels, "values": breakdown_values},
        "marketshare": marketshare,
        "recent_events": recent_events,
        "breakdown_by_category": breakdown_by_category
    }


# ============================================================
# ALLIUM (Staking replacement for ETH)
# ============================================================

def fetch_allium_staking(start_date=None, end_date=None, query_id=None):
    """
    Fetch ETH staking activity from Allium.
    - Uses the best query (STAKERS) that already includes deposits & withdrawals.
    - Normalizes Allium response into a consistent JSON structure.
    - Keeps precomputed daily_net_stake, deposits_est_eth, withdrawals_est_eth from Allium.
    """

    # 1. Select query ID (priority order)
    query_to_use = (
        query_id
        or ALLIUM_QUERY_ID_STAKERS   # ✅ best query: includes withdrawals
        or ALLIUM_QUERY_ID_ACTIVITY  # fallback query: older version
        or ALLIUM_QUERY_ID           # fallback generic
    )

    if not ALLIUM_API_KEY or not query_to_use:
        print("[ALLIUM] Missing API key or query ID", file=sys.stderr)
        return []

    base_url = "https://api.allium.so/api/v1/explorer"
    headers = {"X-API-KEY": ALLIUM_API_KEY, "Content-Type": "application/json"}

    try:
        # 2. Launch query async
        run_url = f"{base_url}/queries/{query_to_use}/run-async"
        payload = {
            "parameters": {"start_date": start_date, "end_date": end_date},
            "run_config": {"limit": 10000}
        }
        run_resp = requests.post(run_url, headers=headers, json=payload, timeout=60)
        run_resp.raise_for_status()
        run_id = run_resp.json().get("run_id")
        if not run_id:
            print("[ALLIUM] No run_id returned from Allium", file=sys.stderr)
            return []

        # 3. Poll query status until it's complete
        status_url = f"{base_url}/query-runs/{run_id}"
        for _ in range(30):  # wait up to ~30 seconds
            status_resp = requests.get(status_url, headers=headers, timeout=30)
            status_resp.raise_for_status()
            if status_resp.json().get("status") == "success":
                break
            time.sleep(1)

        # 4. Fetch query results
        results_url = f"{base_url}/query-runs/{run_id}/results"
        results_resp = requests.get(results_url, headers=headers, timeout=60)
        results_resp.raise_for_status()
        data = results_resp.json().get("data", [])
        if not isinstance(data, list):
            print("[ALLIUM] Invalid response structure", file=sys.stderr)
            return []

        # 5. Normalize ETH rows into consistent format (respecting Allium precomputed fields)
        normalized = []
        for row in data:
            chain_raw = str(row.get("chain_raw", row.get("chain", ""))).lower()
            if chain_raw in ("eth", "ethereum"):
                normalized.append({
                    "activity_date": str(row.get("activity_date")).split("T")[0],
                    "chain": "ethereum",
                    "token_price_at_date": float(row.get("token_price_at_date", 0) or 0),
                    "token_price_current": float(row.get("token_price_current", 0) or 0),
                    "total_stake": float(row.get("total_stake", 0) or 0),
                    "active_stake": float(row.get("active_stake", 0) or 0),
                    "active_stake_usd": float(row.get("active_stake_usd", 0) or 0),
                    "circulating_supply_usd": float(row.get("circulating_supply_usd", 0) or 0),
                    "total_stake_usd_current": float(row.get("total_stake_usd_current", 0) or 0),
                    "active_stake_usd_current": float(row.get("active_stake_usd_current", 0) or 0),
                    "pct_total_stake_active": float(row.get("pct_total_stake_active", 0) or 0),
                    "pct_circulating_staked_est": float(row.get("pct_circulating_staked_est", 0) or 0),
                    "daily_net_stake": float(row.get("daily_net_stake", 0) or 0),
                    "deposits_est_eth": float(row.get("deposits_est_eth", 0) or 0),
                    "withdrawals_est_eth": float(row.get("withdrawals_est_eth", 0) or 0),
                })

        # 6. Sort chronologically
        normalized_sorted = sorted(normalized, key=lambda x: x["activity_date"])

        return normalized_sorted

    except Exception as e:
        print(f"[ALLIUM] Error fetching staking data: {e}", file=sys.stderr)
        return []
    
    
# ============================================================
# SAVE TO SQLITE
# ============================================================
def save_staking_to_db(rows, entities=None):
    if not rows:
        return
    try:
        db_path = os.path.abspath(os.path.join(HERE, "..", "..", "whalescope.db"))
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            for row in rows:
                cur.execute("""
                    INSERT OR REPLACE INTO eth_activity 
                    (activity_date, chain, token_price_at_date, token_price_current,
                     total_stake, active_stake, active_stake_usd, circulating_supply_usd,
                     total_stake_usd_current, active_stake_usd_current,
                     pct_total_stake_active, pct_circulating_staked_est,
                     daily_net_stake, deposits_est_eth, withdrawals_est_eth)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("activity_date"), row.get("chain", "ethereum"),
                    row.get("token_price_at_date"), row.get("token_price_current"),
                    row.get("total_stake"), row.get("active_stake"),
                    row.get("active_stake_usd"), row.get("circulating_supply_usd"),
                    row.get("total_stake_usd_current"), row.get("active_stake_usd_current"),
                    row.get("pct_total_stake_active"), row.get("pct_circulating_staked_est"),
                    row.get("daily_net_stake"), row.get("deposits_est_eth"), row.get("withdrawals_est_eth"),
                ))
            if entities:
                for e in entities:
                    cur.execute("""
                        INSERT OR REPLACE INTO eth_entities
                        (activity_date, entity, staked, share)
                        VALUES (?, ?, ?, ?)
                    """, (e.get("activity_date"), e.get("entity"), e.get("staked"), e.get("share")))
            conn.commit()
    except Exception as e:
        print(f"[DB] Error: {e}", file=sys.stderr)

# ============================================================
# OPENAI INSIGHTS
# ============================================================
def generate_insights(context: dict):
    return {"insight": f"ETH price ${context.get('price')} (24h {context.get('24h_change')}%, 7d {context.get('7d_change')}%, 30d {context.get('30d_change')}%)", "source": "local"}

def get_gpt_insights(staking_rows, context: dict, model="gpt-4o-mini"):
    if not OPENAI_API_KEY:
        return {"insight": "⚠️ No OpenAI API key", "source": "local"}
    try:
        df = pd.DataFrame(staking_rows)
        text = df.tail(30).to_markdown(index=False)
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Analyze ETH staking:\n{text}\n\nContext:\n{json.dumps(context, indent=2)}"}],
            max_tokens=900, temperature=0.6,
        )
        return {"insight": resp.choices[0].message.content.strip(), "source": "OpenAI"}
    except Exception as e:
        return {"insight": f"⚠️ OpenAI error: {e}", "source": "OpenAI"}

# ============================================================
# WHALE DETECTOR - Version B (TradingView-like Whalemap)
# ============================================================


def detect_whale_flows_whalemap(df: pd.DataFrame, symbol: str = "ETH", lookback: int = 7):
    """
    Detecta actividad de ballenas estilo 'Whalemap' (TradingView).
    Devuelve estructura compatible con renderer.js (input_usd/output_usd).
    """

    if df.empty or "volume" not in df.columns or "close" not in df.columns:
        return []

    df = df.copy()
    df["sma_volume"] = df["volume"].rolling(window=lookback, min_periods=1).mean()

    # Flags (igual que TradingView)
    df["f1"] = df["volume"] > df["sma_volume"] * 2.00
    df["f2"] = df["volume"] > df["sma_volume"] * 1.75
    df["f3"] = df["volume"] > df["sma_volume"] * 1.50
    df["f4"] = df["volume"] > df["sma_volume"] * 1.25
    df["f5"] = df["volume"] > df["sma_volume"] * 1.00

    # Buyer vs Seller volume
    df["buyer_vol"] = np.where(df["close"] > df["close"].shift(1), df["volume"], 0)
    df["seller_vol"] = np.where(df["close"] < df["close"].shift(1), df["volume"], 0)

    signals = []
    for _, row in df.iterrows():
        for side in ["buy", "sell"]:
            if (side == "buy" and row["buyer_vol"] == 0) or (side == "sell" and row["seller_vol"] == 0):
                size = 0
                if row["f1"]: size = 5
                elif row["f2"]: size = 4
                elif row["f3"]: size = 3
                elif row["f4"]: size = 2
                elif row["f5"]: size = 1

                if size > 0:
                    signals.append({
                        "timestamp": str(row["dates"]),
                        "input_usd": float(row["volume"]) if side == "buy" else 0,
                        "output_usd": float(row["volume"]) if side == "sell" else 0,
                        "net_flow": float(row["volume"]) if side == "buy" else -float(row["volume"]),
                        "status": side,
                        "symbol": symbol
                    })

    return signals

# ============================================================
# CACHE
# ============================================================
analysis_cache = {}
def get_cached_analysis(key): return analysis_cache.get(key)
def set_cached_analysis(key, value): analysis_cache[key] = value

# ============================================================
# CORE FUNCTION
# ============================================================

def fetch_eth_data(start_date=None, end_date=None):
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    cache_key = f"eth:{start_date}:{end_date}"
    cached = get_cached_analysis(cache_key)
    if cached:
        return cached

    start_ts, end_ts = to_binance_timestamps(start_date, end_date)

    # --- OHLCV (para precio) ---
    url_klines = f"{BINANCE_API_URL}/api/v3/klines"
    params = {
        "symbol": "ETHUSDT",
        "interval": "1d",
        "startTime": start_ts,
        "endTime": end_ts,
        "limit": 1000
    }
    hist = make_request_with_retry(url_klines, params=params) or []
    price_history = {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    for e in hist:
        d = datetime.utcfromtimestamp(e[0] / 1000).strftime("%Y-%m-%d")
        price_history["dates"].append(d)
        price_history["open"].append(float(e[1]))
        price_history["high"].append(float(e[2]))
        price_history["low"].append(float(e[3]))
        price_history["close"].append(float(e[4]))
        price_history["volume"].append(float(e[5]))
    df_price = pd.DataFrame(price_history)

    # --- Spot ---
    spot = make_request_with_retry(f"{BINANCE_API_URL}/api/v3/ticker/24hr", params={"symbol": "ETHUSDT"}) or {}
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
        max_supply = mkt.get("max_supply") or "Unlimited"
    else:
        circulating_supply, max_supply, market_cap, fdv = (
            120_000_000, "Unlimited", price * 120_000_000, price * 120_000_000
        )

    # --- Exchange flows ---
    trades = make_request_with_retry(
        f"{BINANCE_API_URL}/api/v3/aggTrades",
        params={"symbol": "ETHUSDT", "startTime": start_ts, "endTime": end_ts, "limit": 1000}
    ) or []

    df_flows = pd.DataFrame(trades)
    inflows, outflows, net_flow = 0.0, 0.0, 0.0
    if not df_flows.empty:
        df_flows["time"] = pd.to_datetime(df_flows["T"], unit="ms").dt.date
        df_flows["usd_val"] = df_flows["p"].astype(float) * df_flows["q"].astype(float)
        df_flows["side"] = df_flows["m"].map({True: "sell", False: "buy"})

        flows_daily = df_flows.groupby(["time", "side"])["usd_val"].sum().unstack(fill_value=0).reset_index()
        inflows = flows_daily.get("buy", pd.Series(0.0)).sum() / price
        outflows = flows_daily.get("sell", pd.Series(0.0)).sum() / price
        net_flow = inflows - outflows

    # --- Whale detection ---
    top_flows = detect_whale_flows_whalemap(df_price, symbol="ETH") if not df_price.empty else []
    if not top_flows:
        top_flows = [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "net_flow": 0,
            "side": "none",
            "symbol": "ETH"
        }]

    # --- Fees estimate ---
    fees = {"dates": price_history["dates"], "values": [v * 0.0001 for v in price_history["volume"]]}

    # --- Performance ---
    percent_change_7d = (
        (df_price["close"].iloc[-1] - df_price["close"].iloc[-7]) / df_price["close"].iloc[-7] * 100
        if len(df_price) >= 7 else 0
    )
    percent_change_30d = (
        (df_price["close"].iloc[-1] - df_price["close"].iloc[-30]) / df_price["close"].iloc[-30] * 100
        if len(df_price) >= 30 else 0
    )

    # --- Insights (simple, sin GPT) ---
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
        "insights": insights,
        "insights_mode": insights_mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    set_cached_analysis(cache_key, result)
    return result



# ============================================================
# FETCH STAKING ENTITIES 
# ============================================================

def fetch_allium_entities(start_date=None, end_date=None):
    if not ALLIUM_API_KEY or not ALLIUM_QUERY_ID_ENTITIES:
        print("[ALLIUM] Missing API key or query ID (ENTITIES)", file=sys.stderr)
        return []

    base_url = "https://api.allium.so/api/v1/explorer"
    headers = {"X-API-KEY": ALLIUM_API_KEY, "Content-Type": "application/json"}

    try:
        run_url = f"{base_url}/queries/{ALLIUM_QUERY_ID_ENTITIES}/run-async"
        payload = {"parameters": {"start_date": start_date, "end_date": end_date}, "run_config": {"limit": 10000}}
        run_resp = requests.post(run_url, headers=headers, json=payload, timeout=60)
        run_resp.raise_for_status()
        run_id = run_resp.json().get("run_id")
        if not run_id:
            return []

        # Poll status
        status_url = f"{base_url}/query-runs/{run_id}"
        for _ in range(30):
            status_resp = requests.get(status_url, headers=headers, timeout=30)
            status_resp.raise_for_status()
            if status_resp.json().get("status") == "success":
                break
            time.sleep(1)

        # Get results
        results_url = f"{base_url}/query-runs/{run_id}/results"
        results_resp = requests.get(results_url, headers=headers, timeout=60)
        results_resp.raise_for_status()
        data = results_resp.json().get("data", [])

        normalized = []
        for row in data:
            normalized.append({
                "activity_date": str(row.get("activity_date")).split("T")[0],
                "entity": row.get("entity"),
                "staked": float(row.get("deposits_eth", 0) or 0),
                "unstaked": float(row.get("withdrawals_eth", 0) or 0),
                "net_flow": float(row.get("net_flow_eth", 0) or 0),
                "share": None  # opcional
            })
        return normalized

    except Exception as e:
        print(f"[ALLIUM] Error ENTITIES: {e}", file=sys.stderr)
        return []




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

        # ⚠️ Ya no hace falta porque staking_data se guarda dentro de fetch_eth_data
        # if data.get("staking"):
        #     save_staking_to_db(data.get("staking"))

    except Exception as e:
        print(f"[Fatal error] {e}", file=sys.stderr)
        sys.exit(1)

# =====================END eth.py =====================