#!/usr/bin/env python3
# export_pdf_binance_market.py
import os
import re
import sys
import json
import tempfile
import subprocess
from datetime import datetime
import argparse
from textwrap import wrap
from fpdf import FPDF
import plotly.graph_objects as go

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FETCHER = os.path.join(BASE_DIR, "binance_market_fetcher.py")
FONT_PATH = os.path.join(BASE_DIR, "DejaVuSans.ttf")

def run_fetch(symbol, start, end):
    cmd = [sys.executable, FETCHER, symbol, "--start-date", start, "--end-date", end]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout.strip()

    match = re.search(r"(\{.*\})", output, re.DOTALL)
    if not match:
        raise RuntimeError("Could not parse JSON data")
    return json.loads(match.group(1))

def make_chart(fig, outpath):
    fig.update_layout(template="simple_white")
    fig.write_image(outpath)

def make_chart_price(data, outpath):
    candles = data.get("candles", {})
    if candles.get("dates"):
        make_chart(
            go.Figure(data=[go.Candlestick(
                x=candles["dates"], open=candles["open"], high=candles["high"],
                low=candles["low"], close=candles["close"]
            )]),
            outpath
        )

def make_chart_netflow(data, outpath):
    net = data.get("netflow", {})
    if net.get("dates"):
        make_chart(go.Figure(data=[go.Bar(x=net["dates"], y=net["values"])]), outpath)

def make_chart_fees(data, outpath):
    fees = data.get("fees", {})
    if fees.get("dates"):
        make_chart(go.Figure(data=[go.Scatter(x=fees["dates"], y=fees["values"], mode="lines")]), outpath)

def generate_pdf(symbol, start, end, market):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)

    # ✅ Fuente Unicode
    pdf.add_font("DejaVu", "", FONT_PATH)
    pdf.add_font("DejaVu", "B", FONT_PATH)

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

    insight = insight.replace("→", "->").replace("—", "-")

    for ln in wrap(insight, 95):
        pdf.multi_cell(0, 5, ln)
        pdf.ln(1)

    # OUTPUT
    out = os.path.join(tmp, f"WhaleScope_{symbol}_{start}_{end}.pdf")
    pdf.output(out)
    print(out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()

    market = run_fetch(args.symbol, args.start_date, args.end_date)["results"][args.symbol]
    generate_pdf(args.symbol, args.start_date, args.end_date, market)

if __name__ == "__main__":
    main()