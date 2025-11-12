#!/usr/bin/env python3
# export_pdf_allium.py
import os
import sys
import json
import subprocess
import tempfile
from datetime import datetime
from fpdf import FPDF
from markdown import markdown
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FETCH_SCRIPT = os.path.join(BASE_DIR, "staking_analysis.py")

# Detect if it is packaged in the app (DMG)
is_frozen = getattr(sys, "frozen", False)

if is_frozen:
    # DMG → .../WhaleScope.app/Contents/Resources/pyapp/fonts
    FONT_DIR = os.path.join(os.path.dirname(BASE_DIR), "fonts")
else:
    # Dev → python/whalescope_scripts/fonts
    FONT_DIR = os.path.join(BASE_DIR, "fonts")

FONT_PATH = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")


def safe_add_fonts(pdf):
    """
    Add Unicode fonts if they exist; otherwise, use Helvetica.
    """
    try:
        if os.path.exists(FONT_PATH) and os.path.exists(FONT_BOLD_PATH):
            pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
            pdf.add_font("DejaVu", "B", FONT_BOLD_PATH, uni=True)
            return "DejaVu"
        else:
            print("⚠️ DejaVu fonts missing → fallback Helvetica.")
            return "Helvetica"
    except Exception as e:
        print("⚠️ Font load error:", e)
        return "Helvetica"


def clean_text(s):
    if not s:
        return ""
    return s.replace("—", "-").replace("→", "->")


def clean_markdown(md_text):
    if not md_text:
        return ["No insights available."]
    html = markdown(md_text)
    text = BeautifulSoup(html, "html.parser").get_text()
    return [clean_text(line.strip()) for line in text.split("\n") if line.strip()]


def run_fetch(symbol, start, end):
    cmd = [
        sys.executable, FETCH_SCRIPT,
        "--from", start,
        "--to", end,
        "--chains", symbol,
        "--format", "json"
    ]
    result = subprocess.check_output(cmd, text=True)
    return json.loads(result)


def generate_pdf(symbol, start, end, data, chart_path=None):
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    pdf.add_page()

    font = safe_add_fonts(pdf)

    # HEADER
    pdf.set_font(font, "B", 18)
    pdf.cell(0, 10, clean_text(f"WhaleScope - Staking Report ({symbol})"), ln=True)

    pdf.set_font(font, "", 11)
    pdf.cell(0, 5, clean_text(f"Date Range: {start} -> {end}"), ln=True)
    pdf.cell(0, 5, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(8)

    # CHART (si existe)
    if chart_path and os.path.exists(chart_path):
        try:
            pdf.image(chart_path, x=10, w=180)
            pdf.ln(85)
        except:
            pdf.set_font(font, "", 10)
            pdf.cell(0, 6, "(Chart failed to embed)", ln=True)

    # TEXT INSIGHTS
    insights_raw = data.get("results", {}).get(symbol, {}).get("insights", "")
    lines = clean_markdown(insights_raw)

    pdf.set_font(font, "B", 14)
    pdf.cell(0, 7, "Market Insights:", ln=True)
    pdf.set_font(font, "", 11)

    for line in lines:
        pdf.multi_cell(0, 6, line)
        pdf.ln(1)

    # OUTPUT
    out = os.path.join(tempfile.gettempdir(), f"WhaleScope_Allium_{symbol}_{start}_{end}.pdf")
    pdf.output(out)
    print(out)


def main():
    symbol = sys.argv[1]
    start = sys.argv[2]
    end = sys.argv[3]
    chart = sys.argv[4] if len(sys.argv) > 4 else None

    data = run_fetch(symbol, start, end)
    generate_pdf(symbol, start, end, data, chart)


if __name__ == "__main__":
    main()
