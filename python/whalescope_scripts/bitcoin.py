#!/usr/bin/env python3
# ============================================================
# WhaleScope Bitcoin Data Fetcher (with AI Insights)
# ------------------------------------------------------------
# - Binance + CoinGecko for BTC market data
# - Whale activity detection
# - On-chain/market analysis with OpenAI GPT
# - Outputs ONLY JSON (for Electron integration)
# ============================================================

import requests
import json
import argparse
import logging
import time
import random
import os
import hashlib
import sys
import pandas as pd
import numpy as np

from datetime import datetime, timedelta, timezone
from appdirs import user_log_dir
from openai import OpenAI
from market_analysis import generate_trading_advice

# ============================================================
# CONFIGURATION
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
CONFIG_FILE = os.path.join(HERE, "config.json")

def load_config():
    """Load configuration (API keys) from config.json"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg):
    """Save config.json safely"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[Config] Save error: {e}", file=sys.stderr)

def get_api_keys():
    """
    Load API keys with this priority:
    1. Environment variables (used in Electron).
    2. config.json file.
    3. Prompt user (only if running manually in terminal).
    """
    cfg = load_config()

    # 1. Environment variables
    env_keys = {
        "BINANCE_API_KEY": os.getenv("BINANCE_API_KEY"),
        "BINANCE_API_SECRET": os.getenv("BINANCE_API_SECRET"),
        "COINGECKO_API_KEY": os.getenv("COINGECKO_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }
    for k, v in env_keys.items():
        if v:
            cfg[k] = v

    # 2. Prompt user if missing and running interactively
    if sys.stdin.isatty() and (not cfg.get("BINANCE_API_KEY") or not cfg.get("BINANCE_API_SECRET")):
        print("🔑 Configure your API keys for WhaleScope Bitcoin:")
        needed = {
            "BINANCE_API_KEY": "Binance API Key",
            "BINANCE_API_SECRET": "Binance API Secret",
            "COINGECKO_API_KEY": "CoinGecko API Key (optional)",
            "OPENAI_API_KEY": "OpenAI API Key (optional, for AI insights)"
        }
        for key, desc in needed.items():
            if not cfg.get(key):
                val = input(f"Enter {desc} (leave blank to skip): ").strip()
                if val:
                    cfg[key] = val
        save_config(cfg)

    return cfg

CFG = get_api_keys()
API_KEY = CFG.get("BINANCE_API_KEY")
API_SECRET = CFG.get("BINANCE_API_SECRET")
COINGECKO_API_KEY = CFG.get("COINGECKO_API_KEY")
OPENAI_API_KEY = CFG.get("OPENAI_API_KEY")

if not API_KEY or not API_SECRET:
    print("Error: Binance API keys missing", file=sys.stderr)
    sys.exit(1)

BINANCE_API_URL = "https://api.binance.com"

# ============================================================
# LOGGING
# ============================================================

log_dir = user_log_dir("WhaleScope", "Cauco")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "bitcoin.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file,
    filemode="a"
)
logger = logging.getLogger(__name__)

# ============================================================
# CACHING + REQUESTS
# ============================================================

CACHE_DIR = "cache"
CACHE_DURATION = 300  # 5 minutes
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(url):
    return os.path.join(CACHE_DIR, hashlib.md5(url.encode()).hexdigest() + ".json")

def get_cached_response(url):
    """Retrieve response from local cache if valid"""
    cache_file = get_cache_key(url)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if time.time() - cached["timestamp"] < CACHE_DURATION:
                return cached["data"]
        except Exception:
            return None
    return None

def cache_response(url, data):
    """Save response to cache"""
    cache_file = get_cache_key(url)
    with open(cache_file, "w") as f:
        json.dump({"timestamp": time.time(), "data": data}, f, indent=2)

def make_request_with_retry(url, headers=None, params=None, max_retries=3):
    """HTTP GET request with retry + caching"""
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
            elif r.status_code == 429:  # Rate limit
                time.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                return None
        except requests.RequestException:
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt + random.uniform(0, 1))
    return None

def to_binance_timestamps(start_date, end_date):
    """Convert YYYY-MM-DD dates into Binance timestamps"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    start_ts = int(start_dt.replace(hour=0, minute=0, second=0).timestamp() * 1000)
    end_ts = int(end_dt.replace(hour=23, minute=59, second=59).timestamp() * 1000)
    return start_ts, end_ts

# ============================================================
# COINGECKO
# ============================================================

def fetch_coin_gecko_data():
    """Fetch BTC market data from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    headers = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
    data = make_request_with_retry(url, headers=headers)
    if not data:
        return None
    mkt = data.get("market_data", {})
    return {
        "price": mkt.get("current_price", {}).get("usd", 0),
        "market_cap": mkt.get("market_cap", {}).get("usd", 0),
        "fdv": mkt.get("fully_diluted_valuation", {}).get("usd", 0),
        "current_supply": mkt.get("circulating_supply", 0),
        "max_supply": mkt.get("max_supply", 0)
    }
# ============================================================
# WHALE DETECTOR (Whalemap Style v2 - Final)
# ============================================================



def detectar_flows_ballenas(data: pd.DataFrame, symbol: str = "BTC", lookback: int = 14):
    """
    Detecta actividad de ballenas basándose en volumen y dirección de precio.
    Devuelve lista con input_usd, output_usd, net_flow y status.
    """
    if data.empty or not {"open", "close", "volume"}.issubset(data.columns):
        return []

    df = data.copy()
    df["sma_volume"] = df["volume"].rolling(window=lookback, min_periods=1).mean()
    df["buyer_vol"] = np.where(df["close"] > df["open"], df["volume"], 0)
    df["seller_vol"] = np.where(df["close"] < df["open"], df["volume"], 0)

    signals = []
    for i, row in df.iterrows():
        vol = row["volume"]
        avg_vol = row["sma_volume"]
        side = None

        # 🔍 Volumen inusualmente alto
        if vol > avg_vol * 1.8:  # más sensible que antes
            if row["close"] > row["open"]:
                side = "buy"
            elif row["close"] < row["open"]:
                side = "sell"

        if side:
            price_usd = float(row["close"])
            usd_val = vol * price_usd
            signals.append({
                "timestamp": str(row.get("dates", row.name)),
                "input_usd": usd_val if side == "buy" else 0,
                "output_usd": usd_val if side == "sell" else 0,
                "net_flow": usd_val if side == "buy" else -usd_val,
                "status": f"whale_{side}",
                "symbol": symbol
            })

    # ⚙️ Si no detectó nada, toma los últimos días como referencia
    if not signals and len(df) > 0:
        last_rows = df.tail(5)
        for _, row in last_rows.iterrows():
            price_usd = float(row["close"])
            usd_val = row["volume"] * price_usd
            signals.append({
                "timestamp": str(row.get("dates", row.name)),
                "input_usd": usd_val * 0.6,
                "output_usd": usd_val * 0.4,
                "net_flow": usd_val * 0.2,
                "status": "neutral",
                "symbol": symbol
            })

    return signals

# ============================================================
# AI INSIGHTS
# ============================================================

def generate_insights(context: dict):
    """Simple fallback analysis if GPT fails"""
    return {
        "insight": f"Basic analysis: BTC price ${context.get('price')} "
                   f"(24h {context.get('24h_change')}%, "
                   f"7d {context.get('7d_change')}%, "
                   f"30d {context.get('30d_change')}%).",
        "source": "local"
    }

def get_gpt_insights(price_history, context: dict, model="gpt-4o-mini"):
    """Ask OpenAI GPT to produce a professional BTC report"""
    if not OPENAI_API_KEY:
        return {"insight": "⚠️ No OpenAI API key available", "source": "local"}

    if not price_history or not isinstance(price_history, dict):
        return {"insight": "⚠️ No market insights available", "source": "local"}

    df = pd.DataFrame(price_history)
    text = df.tail(30).to_markdown(index=False)

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""
You are a senior blockchain analyst. Use reliable sources like Glassnode, CoinMetrics, and industry reports.
Analyze Bitcoin market and on-chain data (snapshot: {datetime.now(timezone.utc).strftime('%B %d, %Y')}).
Provide a professional report with:

1. **Current Market Overview**
2. **On-chain Insights**
   - Addresses
   - Transactions
   - Fees
   - Miner flows
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
# CORE FUNCTION
# ============================================================

def fetch_bitcoin_data(start_date=None, end_date=None):
    """Fetch Bitcoin data from Binance, CoinGecko, and generate insights"""
    # Default date range (last 30 days)
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    start_ts, end_ts = to_binance_timestamps(start_date, end_date)

    # ----------------- OHLCV (candlestick data) -----------------
    url_klines = f"{BINANCE_API_URL}/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "1d", "startTime": start_ts, "endTime": end_ts, "limit": 1000}
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

    # ----------------- Spot Binance -----------------
    url_ticker = f"{BINANCE_API_URL}/api/v3/ticker/24hr"
    spot = make_request_with_retry(url_ticker, params={"symbol": "BTCUSDT"}) or {}
    price = float(spot.get("lastPrice", 0))
    percent_change_24h = float(spot.get("priceChangePercent", 0))
    volume_24h = float(spot.get("volume", 0)) * price

    # ----------------- CoinGecko Market Stats -----------------
    gecko = fetch_coin_gecko_data()
    if gecko:
        market_cap = gecko["market_cap"]
        fdv = gecko["fdv"]
        circulating_supply = gecko["current_supply"]
        max_supply = gecko["max_supply"]
    else:
        circulating_supply = 19700000  # fallback
        max_supply = 21000000
        market_cap = price * circulating_supply
        fdv = price * max_supply

    # ----------------- Exchange Flows -----------------
    url_trades = f"{BINANCE_API_URL}/api/v3/aggTrades"
    trades = make_request_with_retry(url_trades, params={"symbol": "BTCUSDT", "limit": 1000}) or []
    inflows, outflows = 0, 0
    for t in trades:
        usd_val = float(t["p"]) * float(t["q"])
        if t["m"]:
            outflows += usd_val
        else:
            inflows += usd_val
    inflows = inflows / price if price > 0 else 0
    outflows = outflows / price if price > 0 else 0
    net_flow = inflows - outflows

    
    # ----------------- Whale Detection (Whalemap Style) -----------------
    top_flows = detectar_flows_ballenas(df, symbol="BTC") if not df.empty else []

    if not top_flows:
     top_flows = [{
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_usd": 0,
        "output_usd": 0,
        "net_flow": 0,
        "status": "none",
        "symbol": "BTC"
    }]

    # ----------------- Fees Estimate -----------------
    fees = {"dates": price_history["dates"], "values": [v * 0.0001 for v in price_history["volume"]]}

    # ----------------- Performance Metrics -----------------
    percent_change_7d, percent_change_30d = 0, 0
    if len(df) >= 7:
        try:
            percent_change_7d = (df["close"].iloc[-1] - df["close"].iloc[-7]) / df["close"].iloc[-7] * 100
        except Exception:
            pass
    if len(df) >= 30:
        try:
            percent_change_30d = (df["close"].iloc[-1] - df["close"].iloc[-30]) / df["close"].iloc[-30] * 100
        except Exception:
            pass

    support_level = min(price_history["low"]) if price_history["low"] else 0
    whale_tx = top_flows[0]["input_usd"]

    # ----------------- AI Insights (Pro → fallback Basic) -----------------
    insights_mode = "basic"
    try:
        insights = get_gpt_insights(price_history, {
            "price": price,
            "24h_change": percent_change_24h,
            "7d_change": percent_change_7d,
            "30d_change": percent_change_30d,
            "net_flow": net_flow,
            "whale_tx": whale_tx,
            "date_range": {"start": start_date, "end": end_date}
        })
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

    # ----------------- Trading Advice -----------------
    analysis = generate_trading_advice(price, percent_change_24h, net_flow, whale_tx, support_level, df, asset="BTC")

    # ----------------- Market Conclusion -----------------
    conclusion = "Neutral market."
    if percent_change_24h < 0 and net_flow < 0:
        conclusion = "Bearish short-term, but whale accumulation suggests rebound."
    elif percent_change_24h > 0 and net_flow < 0:
        conclusion = "Bullish trend supported by whale accumulation."
    elif percent_change_24h > 0 and net_flow > 0:
        conclusion = "Bullish but inflows suggest potential profit-taking."

    # ----------------- Return JSON -----------------
    return {
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
        "analysis": analysis,
        "conclusion": conclusion,
        "insights": insights,
        "insights_mode": insights_mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bitcoin data fetcher")
    parser.add_argument("--start-date", type=str)
    parser.add_argument("--end-date", type=str)
    args = parser.parse_args()

    try:
        data = fetch_bitcoin_data(args.start_date, args.end_date)
        sys.stdout.write(json.dumps(data))
        sys.stdout.flush()
    except Exception as e:
        print(f"[Fatal error] {e}", file=sys.stderr)
        sys.exit(1)