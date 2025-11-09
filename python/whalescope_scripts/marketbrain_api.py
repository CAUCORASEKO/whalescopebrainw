#!/usr/bin/env python3
"""
marketbrain_api.py
API Flask para servir datos de marketbrain.db a la UI + exportación CSV/PDF
(Versión final: tablas ajustadas, formato numérico, limpieza de nulos, layout en landscape, e inclusión automática de todos los símbolos)
"""

from flask import Flask, jsonify, request, send_file
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)

DB_PATH = "/Users/cauco/Desktop/whalescope-desktop/whalescope/python/whalescope_scripts/marketbrain.db"

# ============================================================
# 🔹 Utilidades
# ============================================================

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()
    data = [dict(row) for row in rows]
    return (data[0] if data else None) if one else data

# ============================================================
# 🔹 Endpoints básicos
# ============================================================

@app.route("/api/symbol/<symbol>")
def get_symbol_data(symbol):
    symbol = symbol.upper()
    staking = query_db("SELECT * FROM staking_data WHERE symbol = ? ORDER BY activity_date DESC LIMIT 365", (symbol,))
    whales = query_db("SELECT * FROM whale_signals WHERE symbol = ? ORDER BY timestamp DESC LIMIT 100", (symbol,))
    return jsonify({
        "symbol": symbol,
        "staking_data": staking,
        "whale_signals": whales,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/symbols")
def list_symbols():
    symbols = query_db("SELECT DISTINCT symbol FROM staking_data")
    return jsonify([s["symbol"] for s in symbols])

@app.route("/")
def root():
    return jsonify({
        "status": "✅ MarketBrain API running",
        "endpoints": {
            "/api/symbol/<symbol>": "Datos de staking + whale detector para un símbolo",
            "/api/symbols": "Lista de símbolos disponibles",
            "/api/export_csv": "Exportar staking_data a CSV",
            "/api/export_pdf": "Exportar staking_data a PDF (por símbolo con resumen global)"
        }
    })

# ============================================================
# 🧩 EXPORT CSV (todos los símbolos automáticamente)
# ============================================================

@app.route("/api/export_csv")
def export_csv():
    symbols_param = request.args.get("symbols")
    if symbols_param:
        symbols = symbols_param.split(",")
    else:
        all_symbols = query_db("SELECT DISTINCT symbol FROM staking_data")
        symbols = [s["symbol"] for s in all_symbols]

    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    columns = [
        "symbol", "activity_date",
        "total_stake", "active_stake", "active_stake_usd_current",
        "pct_total_stake_active", "pct_circulating_staked_est",
        "token_price", "net_flow", "deposits_est", "withdrawals_est"
    ]

    query = f"""
        SELECT {', '.join(columns)}
        FROM staking_data
        WHERE symbol IN ({','.join(['?'] * len(symbols))})
    """
    params = symbols
    if start_date:
        query += " AND activity_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND activity_date <= ?"
        params.append(end_date)
    query += " ORDER BY symbol, activity_date ASC"

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(query, conn, params=params)

    if df.empty:
        return jsonify({"error": "No data found for selection"}), 404

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="marketbrain_export_full.csv"
    )

# ============================================================
# 🧠 EXPORT PDF (todos los símbolos automáticamente)
# ============================================================

@app.route("/api/export_pdf")
def export_pdf():
    return {"error": "❌ Deprecated endpoint. Use desktop Export PDF button."}, 410

# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)