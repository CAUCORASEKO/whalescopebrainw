#!/usr/bin/env python3
import os
import sys
import json
import tempfile
import argparse
from datetime import datetime
from textwrap import wrap
import requests
from fpdf import FPDF
import plotly.graph_objects as go

API_URL = "http://127.0.0.1:5001/api/binance_market"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")

# ------------------------------
# Fetch data from backend Flask
# ------------------------------



def fetch_from_backend(symbol, start, end):
    url = (
        f"http://127.0.0.1:5001/api/binance_market"
        f"?symbol={symbol}"
        f"&startDate={start}"
        f"&endDate={end}"
    )

    # ❗ NO IMPRIMAS NADA AQUÍ
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Backend request failed: {e}")

    if (
        not isinstance(data, dict)
        or "results" not in data
        or symbol not in data["results"]
    ):
        raise RuntimeError(
            f"Backend response does not contain expected data for {symbol}"
        )

    return data["results"][symbol]



# ------------------------------
# Chart helpers
# ------------------------------
def make_chart(fig, outpath):
    fig.update_layout(template="simple_white")
    fig.write_image(outpath)

def make_chart_price(data, outpath):
    candles = data.get("candles", {})
    if candles.get("dates"):
        fig = go.Figure(
            data=[go.Candlestick(
                x=candles["dates"],
                open=candles["open"], high=candles["high"],
                low=candles["low"], close=candles["close"]
            )]
        )
        make_chart(fig, outpath)

def make_chart_netflow(data, outpath):
    net = data.get("netflow", {})
    if net.get("dates"):
        fig = go.Figure(data=[go.Bar(x=net["dates"], y=net["values"])])
        make_chart(fig, outpath)

def make_chart_fees(data, outpath):
    fees = data.get("fees", {})
    if fees.get("dates"):
        fig = go.Figure(data=[go.Scatter(x=fees["dates"], y=fees["values"], mode="lines")])
        make_chart(fig, outpath)


# ------------------------------
# PDF generation
# ------------------------------
def generate_pdf(symbol, start, end, market):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)

    pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
    pdf.add_font("DejaVu", "B", FONT_PATH, uni=True)

    pdf.add_page()

    # HEADER
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 10, f"WhaleScope Market Report - {symbol}", ln=True)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 6, f"Date Range: {start} -> {end}", ln=True)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(4)

    # MARKET STATS
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, "Market Statistics:", ln=True)

    pdf.set_font("DejaVu", "", 12)
    stats = market.get("markets", {})

    for k, v in stats.items():
        safe = f"{k}: {v}".replace("→", "->").replace("—", "-")
        for ln in wrap(safe, 95):
            pdf.multi_cell(0, 5, ln)
        pdf.ln(1)

    pdf.ln(5)

    # CHARTS
    tmp = tempfile.gettempdir()
    charts = [
        (make_chart_price, os.path.join(tmp, f"{symbol}_price.png")),
        (make_chart_netflow, os.path.join(tmp, f"{symbol}_netflow.png")),
        (make_chart_fees, os.path.join(tmp, f"{symbol}_fees.png")),
    ]

    for func, img_path in charts:
        func(market, img_path)
        if os.path.exists(img_path):
            pdf.image(img_path, w=165)
            pdf.ln(4)

    # AI INSIGHTS
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, "AI Market Insights:", ln=True)

    pdf.set_font("DejaVu", "", 12)
    insight = market.get("insights")

    if isinstance(insight, dict):
        insight = insight.get("analysis") or json.dumps(insight, indent=2)

    if not insight:
        insight = "No AI insights available."

    insight = insight.replace("→","->").replace("—","-")

    for ln in wrap(insight, 95):
        pdf.multi_cell(0, 5, ln)
        pdf.ln(1)

    # OUTPUT
    out = os.path.join(tmp, f"WhaleScope_{symbol}_{start}_{end}.pdf")
    pdf.output(out)
    print(out)


# ------------------------------
# MAIN
# ------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()

    # *** FIX: Fetch directly from backend ***
    market = fetch_from_backend(args.symbol, args.start_date, args.end_date)
    generate_pdf(args.symbol, args.start_date, args.end_date, market)


if __name__ == "__main__":
    main()
