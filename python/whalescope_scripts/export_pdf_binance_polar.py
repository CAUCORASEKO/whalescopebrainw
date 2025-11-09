#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import tempfile
from datetime import datetime
from fpdf import FPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FETCHER = os.path.join(BASE_DIR, "binance_polar.py")


def run_fetch():
    """Run Binance Polar script and capture JSON."""
    cmd = [sys.executable, FETCHER, "--format", "json"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)

    try:
        return json.loads(result.stdout.strip())
    except:
        raise RuntimeError("Failed to parse JSON output from binance_polar")


def generate_pdf(data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "WhaleScope Polar Report", ln=True)

    # Subtext
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(4)

    table = data.get("table", [])
    if not table:
        pdf.set_font("Helvetica", "I", 12)
        pdf.cell(0, 10, "No whale wallet clustering data available.", ln=True)
    else:
        headers = list(table[0].keys())

        # Header Row
        pdf.set_font("Helvetica", "B", 10)
        col_width = pdf.w / len(headers) - 2
        for h in headers:
            pdf.cell(col_width, 7, h, border=1)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 9)
        for row in table:
            for h in headers:
                pdf.cell(col_width, 7, str(row[h]), border=1)
            pdf.ln()

    # Summary
    total = data.get("total_balances", "N/A")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Total Value Across Identified Wallets: {total}", ln=True)

    # ✅ Always generate unique filename (prevents overwriting)
    outfile = os.path.join(
        tempfile.gettempdir(),
        f"WhaleScope_BinancePolar_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    pdf.output(outfile)
    return outfile


def main():
    data = run_fetch()
    pdf_path = generate_pdf(data)
    print(pdf_path)


if __name__ == "__main__":
    main()