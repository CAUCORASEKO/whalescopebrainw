#!/usr/bin/env python3
# ============================================================
# WhaleScope Binance Market Fetcher (Smart Money + Accumulation Score)
# ------------------------------------------------------------
# - OHLCV & aggTrades desde Binance (No Allium/Arkham)
# - Whale Exchange Net Flow Detector
# - Smart Money Phase + Accumulation Score (0–100)
# - AI Insights usando GPT si OPENAI_API_KEY existe
# - binnace_market_fetcher.py
# ============================================================

import sys
import time
import json
import random
import os
import requests
import argparse
import pandas as pd
import math

import matplotlib
matplotlib.use('Agg')  # ✅ required in Electron (without UI)
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from datetime import datetime, timedelta
from whales_detector import detect_whale_flows
from openai import OpenAI
from eth import detect_whale_flows_whalemap

BINANCE_API_URL = "https://api.binance.com"


def load_stored_api_key():
    config_path = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                # ✅ First try new format
                if "OPENAI_API_KEY" in data:
                    return data["OPENAI_API_KEY"]
                # ✅ Then try old nested format
                return data.get("openai", {}).get("OPENAI_API_KEY")
        except:
            pass
    return None

# ------------------------ LOAD BINANCE API KEYS ------------------------
def load_binance_keys():
    config_path = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                key = data.get("BINANCE_API_KEY")
                secret = data.get("BINANCE_API_SECRET")
                if key and secret:
                    return key, secret
        except:
            pass
    return None, None

BINANCE_API_KEY, BINANCE_API_SECRET = load_binance_keys()

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    print("⚠️ Binance API keys missing — continuing without authenticated endpoints")
else:
    os.environ["BINANCE_API_KEY"] = BINANCE_API_KEY
    os.environ["BINANCE_API_SECRET"] = BINANCE_API_SECRET

# ------------------------ FIX JSON (elimina NaN) ------------------------
def clean_nan(obj):
    if isinstance(obj, list):
        return [clean_nan(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, float) and math.isnan(obj):
        return 0
    return obj


# ------------------------ HELPERS ------------------------
def make_request(url, params=None, retries=3):
    for _ in range(retries):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(1.2 + random.random())
                continue
            return None
        except:
            time.sleep(1.2)
    return None


def to_ts_range(start_date, end_date):
    s = datetime.strptime(start_date, "%Y-%m-%d")
    e = datetime.strptime(end_date, "%Y-%m-%d")
    return int(s.timestamp()*1000), int((e+timedelta(days=1)).timestamp()*1000)


# ------------------------ EXCHANGE FLOWS ------------------------
def fetch_aggregated_flows(symbol, start_date, end_date):
    start_ts, end_ts = to_ts_range(start_date, end_date)
    step = 24*60*60*1000
    rows = []

    t = start_ts
    while t < end_ts:
        end = min(t+step, end_ts)
        data = make_request(f"{BINANCE_API_URL}/api/v3/aggTrades", {
            "symbol": f"{symbol}USDT",
            "startTime": t,
            "endTime": end,
            "limit": 1000
        })

        inflow = outflow = price = 0.0
        if data:
            for tr in data:
                q = float(tr["q"])
                p = float(tr["p"])
                usd = q*p
                price = p
                if tr["m"]:
                    outflow += usd
                else:
                    inflow += usd

        rows.append({
            "timestamp": datetime.utcfromtimestamp(t/1000).strftime("%Y-%m-%d"),
            "inflow_usd": inflow,
            "outflow_usd": outflow,
            "net_flow_usd": inflow - outflow,
            "close_price": price
        })

        t = end
        time.sleep(0.12)

    return pd.DataFrame(rows)



def fetch_liquidity_pressure(symbol, start_date, end_date):
    url = f"{BINANCE_API_URL}/futures/data/takerlongshortRatio"
    params = {
        "symbol": f"{symbol}USDT",
        "period": "1d",
        "limit": 30
    }
    data = make_request(url, params)

    dates, pressure = [], []
    if data:
        for row in data:
            dates.append(datetime.utcfromtimestamp(int(row["timestamp"])/1000).strftime("%Y-%m-%d"))
            buy = float(row["buyVol"])
            sell = float(row["sellVol"])
            score = (buy - sell) / (buy + sell + 1e-9)
            pressure.append(score)

    return {"dates": dates, "pressure": pressure}


# ------------------------ SMART MONEY PHASE ------------------------
def smart_money_phase(df_flows, df_prices):
    if df_flows.empty or df_prices.empty:
        return "No Data"

    df_flows["ma7"] = df_flows["net_flow_usd"].rolling(7).mean()

    slope = df_flows["ma7"].iloc[-1] - df_flows["ma7"].iloc[-7] if len(df_flows) >= 14 else 0
    price_change = df_prices["close"].iloc[-1] - df_prices["close"].iloc[-7] if len(df_prices) >= 7 else 0

    if slope > 0 and price_change < 0:
        return "Acumulación"
    if slope > 0 and price_change > 0:
        return "Markup (Trend Up)"
    if slope < 0 and price_change > 0:
        return "Distribución"
    if slope < 0 and price_change < 0:
        return "Markdown (Trend Down)"
    return "Neutral"


# ------------------------ ACCUMULATION SCORE ------------------------
def accumulation_score(df_flows, df_prices, whales_count):
    if df_flows.empty:
        return 50

    df_flows["ma7"] = df_flows["net_flow_usd"].rolling(7).mean()

    slope = df_flows["ma7"].iloc[-1] - df_flows["ma7"].iloc[-7] if len(df_flows) >= 14 else 0
    price_change = df_prices["close"].iloc[-1] - df_prices["close"].iloc[-7] if len(df_prices) >= 7 else 0

    slope_score = max(min((slope / abs(df_flows["ma7"].std() + 1e-9)) * 50 + 50, 100), 0)
    price_score = max(min((price_change / abs(df_prices["close"].std() + 1e-9)) * 40 + 50, 100), 0)
    whale_score = min(whales_count * 5, 100)

    score = (slope_score * 0.45) + (price_score * 0.35) + (whale_score * 0.20)
    return round(score)


# ------------------------ AI INSIGHTS ------------------------
def generate_ai_insights(symbol, phase, score):
    api_key = os.environ.get("OPENAI_API_KEY") or load_stored_api_key()
    if not api_key:
        return None

    client = OpenAI(api_key=api_key)

    prompt = f"""
Explain the current Smart Money behavior for {symbol}.
Smart Money Phase: {phase}
Accumulation Score: {score}/100
Write 6 concise sentences.
Focus on whales, trend bias and key risks.
No emojis.
"""

    try:
        r = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}]
        )
        return r.choices[0].message.content.strip()
    except:
        return None


def export_pdf(symbol, df_prices, df_flows, whales_exchange, phase, score, insights, output_path):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{symbol} — Smart Money Market Report</b>", styles['Title']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Smart Money Phase: <b>{phase}</b>", styles['Heading2']))
    story.append(Paragraph(f"Accumulation Score: <b>{score}/100</b>", styles['Heading3']))
    story.append(Spacer(1, 28))

    if insights:
        story.append(Paragraph("<b>AI Insights</b>", styles['Heading2']))
        story.append(Paragraph(insights.replace("\n", "<br/>"), styles['BodyText']))
        story.append(Spacer(1, 24))

    # ===== CHART 1: PRICE =====
    price_chart_path = f"/tmp/{symbol}_price.png"
    plt.figure(figsize=(6,3))
    plt.plot(df_prices["dates"], df_prices["close"])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(price_chart_path)
    plt.close()
    story.append(Paragraph("<b>Price Action</b>", styles['Heading2']))
    story.append(Image(price_chart_path, width=450, height=180))
    story.append(Spacer(1, 24))

    # ===== CHART 2: NETFLOW =====
    netflow_chart_path = f"/tmp/{symbol}_netflow.png"
    plt.figure(figsize=(6,3))
    plt.bar(df_flows["timestamp"], df_flows["net_flow_usd"])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(netflow_chart_path)
    plt.close()
    story.append(Paragraph("<b>Whale Netflow</b>", styles['Heading2']))
    story.append(Image(netflow_chart_path, width=450, height=180))
    story.append(Spacer(1, 24))

    # ===== TABLE: WHALES =====
    if whales_exchange:
        story.append(Paragraph("<b>Whale Activity</b>", styles['Heading2']))
        table_data = [["Date", "Inflow (USD)", "Outflow (USD)", "Status"]]
        for w in whales_exchange:
            table_data.append([
                w.get("date",""),
                w.get("input_usd", 0),
                w.get("output_usd", 0),
                w.get("status","")
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#222")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.4, colors.grey),
        ]))
        story.append(table)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    doc.build(story)
    return output_path




# ------------------------ MAIN FETCH ------------------------

def fetch_binance_market(symbol, start_date, end_date):
    symbol = symbol.upper()
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    s_ts, e_ts = to_ts_range(start_date, end_date)

    # --- OHLCV (para precio) ---
    klines = make_request(f"{BINANCE_API_URL}/api/v3/klines", {
        "symbol": f"{symbol}USDT",
        "interval": "1d",
        "startTime": s_ts,
        "endTime": e_ts,
        "limit": 1000
    }) or []

    hist = {
        "dates": [datetime.utcfromtimestamp(e[0]/1000).strftime("%Y-%m-%d") for e in klines],
        "open": [float(e[1]) for e in klines],
        "high": [float(e[2]) for e in klines],
        "low": [float(e[3]) for e in klines],
        "close": [float(e[4]) for e in klines],
        "volume": [float(e[5]) for e in klines]
    }
    df_prices = pd.DataFrame(hist)
    price = hist["close"][-1] if hist["close"] else None

    # ✅ Whale Detection (matching ETH logic)
    df_price_for_whales = pd.DataFrame(hist)
    whales_exchange = detect_whale_flows_whalemap(df_price_for_whales, symbol=symbol)

    # ✅ Whale Activity Table (matches UI of ETH)
    whale_table = []
    for w in whales_exchange:
        ts = w.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
        except:
            pass
        whale_table.append({
            "date": ts,
            "input_usd": round(float(w.get("input_usd", 0)), 2),
            "output_usd": round(float(w.get("output_usd", 0)), 2),
            "status": w.get("status", "neutral")
        })

    # --- Aggregated Flows for NETFLOW chart ---
    df_flows = fetch_aggregated_flows(symbol, start_date, end_date)

    # --- Smart Money + Score ---
    phase = smart_money_phase(df_flows, df_prices)
    score = accumulation_score(df_flows, df_prices, len(whales_exchange))

    # --- PERFORMANCE ---
    perf = {}
    if len(hist["close"]) >= 30:
        perf["percent_change_24h"] = round(((hist["close"][-1] / hist["close"][-2]) - 1) * 100, 2)
        perf["percent_change_7d"] = round(((hist["close"][-1] / hist["close"][-7]) - 1) * 100, 2)
        perf["percent_change_30d"] = round(((hist["close"][-1] / hist["close"][-30]) - 1) * 100, 2)

    # --- Market Stats ---
    from token_fundamentals import get_token_fundamentals
    fund = get_token_fundamentals(symbol)

    market_cap = fund.get("market_cap")
    fdv = fund.get("fdv")
    supply = fund.get("current_supply")
    max_supply = fund.get("max_supply")
        

    # --- Fees Chart (same as ETH) ---
    fees = {
        "dates": hist["dates"],
        "values": [v * 0.0001 for v in hist["volume"]] if hist["volume"] else []
    }

        # --- Netflow chart (uses flows) ---
    netflow = {
        "dates": df_flows["timestamp"].tolist() if not df_flows.empty else [],
        "values": df_flows["net_flow_usd"].tolist() if not df_flows.empty else []
    }

    # ✅ Here we activate OpenAI
    insights = generate_ai_insights(symbol, phase, score)


    if os.environ.get("EXPORT_MODE") == "pdf":
        output_file = f"/tmp/{symbol}_report.pdf"
        export_pdf(symbol, df_prices, df_flows, whale_table, phase, score, insights, output_file)
        return {"file": output_file}

    return clean_nan({
        "results": {
            symbol: {
                "markets": {
                    "price": price,
                    "volume_24h": hist["volume"][-1] if hist["volume"] else None,
                    "market_cap": market_cap,
                    "fdv": fdv,
                    "current_supply": supply,
                    "max_supply": max_supply,
                },
                "performance": perf,
                "candles": hist,
                "whales_table": whale_table,
                "whales_combined": whales_exchange,
                "netflow": netflow,
                "fees": fees,
                "smart_money_phase": phase,
                "accumulation_score": score,
                "insights": insights  # ✅ AI now real
            }
        }
    })
    


# ------------------------ CLI ------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("--start-date")
    p.add_argument("--end-date")
    a = p.parse_args()

    result = fetch_binance_market(a.symbol, a.start_date, a.end_date)
    print(json.dumps(result, indent=2))