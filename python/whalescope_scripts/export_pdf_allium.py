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

# -----------------------------------------------------------
# 🎯 Ruta de fuentes correcta (DEV vs DMG) + fallback
# -----------------------------------------------------------
is_frozen = getattr(sys, "frozen", False) or "pyapp" in BASE_DIR

if is_frozen:
    # ✅ DMG: .../Resources/pyapp/fonts
    BASE_FONT_DIR = os.path.join(os.path.dirname(BASE_DIR), "fonts")
else:
    # ✅ DEV: .../python/fonts  (solo 1 nivel arriba)
    BASE_FONT_DIR = os.path.join(os.path.dirname(BASE_DIR), "fonts")

FONT_PATH = os.path.join(BASE_FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(BASE_FONT_DIR, "DejaVuSans-Bold.ttf")


def safe_add_fonts(pdf):
    """
    Agrega las fuentes personalizadas si existen.
    Si no → usa Helvetica (fuente interna de FPDF, siempre disponible).
    """
    try:
        if not os.path.exists(FONT_PATH) or not os.path.exists(FONT_BOLD_PATH):
            raise FileNotFoundError("Missing font files")
        pdf.add_font("Clean", "", FONT_PATH)
        pdf.add_font("CleanB", "", FONT_BOLD_PATH)
        return "Clean", "CleanB"
    except:
        return "Helvetica", "Helvetica"


def clean_markdown(md_text):
    if not md_text:
        return ["No insights available."]
    html = markdown(md_text)
    text = BeautifulSoup(html, "html.parser").get_text()
    return [line.strip() for line in text.split("\n") if line.strip()]


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

    normal_font, bold_font = safe_add_fonts(pdf)

    # HEADER
    pdf.set_font(bold_font, "", 18)
    pdf.cell(0, 10, f"WhaleScope — Staking Report ({symbol})", ln=True)

    pdf.set_font(normal_font, "", 11)
    pdf.cell(0, 5, f"Date Range: {start} → {end}", ln=True)
    pdf.cell(0, 5, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(8)

    # CHART
    if chart_path and os.path.exists(chart_path):
        try:
            pdf.image(chart_path, x=10, y=None, w=180)
            pdf.ln(85)
        except:
            pdf.ln(5)
            pdf.set_font(normal_font, "", 10)
            pdf.cell(0, 6, "(Chart failed to embed)", ln=True)

    # INSIGHTS
    insights_raw = data.get("results", {}).get(symbol, {}).get("insights", "")
    insights_lines = clean_markdown(insights_raw)

    pdf.set_font(bold_font, "", 14)
    pdf.cell(0, 7, "Market Insights:", ln=True)
    pdf.set_font(normal_font, "", 11)

    for line in insights_lines:
        pdf.multi_cell(0, 6, line)
        pdf.ln(1)

    # SAVE TEMP FILE
    out = os.path.join(tempfile.gettempdir(), f"WhaleScope_Allium_{symbol}_{start}_{end}.pdf")
    pdf.output(out)
    print(out)


def main():
    symbol = sys.argv[1]
    start = sys.argv[2]
    end = sys.argv[3]
    chart_path = sys.argv[4] if len(sys.argv) > 4 else None

    data = run_fetch(symbol, start, end)
    generate_pdf(symbol, start, end, data, chart_path)


if __name__ == "__main__":
    main()