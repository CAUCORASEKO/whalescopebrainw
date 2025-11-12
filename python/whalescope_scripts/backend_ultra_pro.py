#!/usr/bin/env python3
"""
WhaleScope Ultra-Pro Backend
Flask API that bridges Electron frontend with Python scripts
backend_ultra_pro.py
"""
import pandas as pd
import os
import sys
import json
import subprocess
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import send_file, Response
from flask import send_file

# =========================================================
# 🧾 Logging Setup
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("backend")

# =========================================================
# 🔐 Load API Keys (saved by Electron UI)
# =========================================================
CONFIG_PATH = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")

def load_api_keys():
    keys = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                keys = json.load(f)
        except:
            pass

    # ✅ Export to environment for staking_analysis & Allium
    for k, v in keys.items():
        if v:
            os.environ[k] = v

    return keys

API_KEYS = load_api_keys()
logger.info(f"🔑 Loaded API Keys: {list(API_KEYS.keys())}")

# =========================================================
# 🧩 Flask App Init
# =========================================================
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = {
    "bitcoin": os.path.join(BASE_DIR, "bitcoin.py"),
    "eth": os.path.join(BASE_DIR, "eth.py"),
    "binance_polar": os.path.join(BASE_DIR, "binance_polar.py"),
    "marketbrain": os.path.join(BASE_DIR, "staking_analysis.py"),
    "binance-market": os.path.join(BASE_DIR, "binance_market_fetcher.py"),
    "binance-market-pdf": os.path.join(BASE_DIR, "export_pdf_binance_market.py"),  
    "allium-pdf": os.path.join(BASE_DIR, "export_pdf_allium.py"),
    "binance-polar-pdf": os.path.join(BASE_DIR, "export_pdf_binance_polar.py"),
}

# =========================================================
# ⚙️ Helper: Run Python script and capture JSON
# =========================================================
def run_script(script, args=None):
    """Run a Python script and return parsed JSON output"""
    if not os.path.exists(script):
        return {"status": "error", "message": f"Script not found: {script}"}

    cmd = [sys.executable, script]
    if args:
        cmd.extend(args)

    logger.info(f"🚀 Running script: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180
        )

        if result.stderr:
            logger.warning(f"[stderr from {os.path.basename(script)}]\n{result.stderr}")

        output = result.stdout.strip()
        if not output:
            logger.warning(f"⚠️ Empty stdout from {os.path.basename(script)}")
            return {"status": "error", "message": "Empty output from script"}

        # Extract JSON safely
        import re
        match = re.search(r"(\{.*\}|\[.*\])", output, re.DOTALL)
        json_part = match.group(0) if match else output

        try:
            return json.loads(json_part)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON from {script}: {e}")
            return {"status": "error", "message": f"Invalid JSON: {e}", "raw_output": output[:500]}

    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Timeout while running {script}")
        return {"status": "error", "message": "Timeout while running script"}
    except Exception as e:
        logger.exception(f"❌ Unexpected error running {script}: {e}")
        return {"status": "error", "message": str(e)}

# =========================================================
# 🌐 Health Check
# =========================================================
@app.route("/")
def health():
    return jsonify({
        "ok": True,
        "service": "whalescope-backend",
        "version": "ultra-pro",
        "time": datetime.utcnow().isoformat()
    })

# =========================================================
# 📈 Bitcoin Endpoint
# =========================================================
@app.route("/api/bitcoin")
def api_bitcoin():
    start = request.args.get("startDate")
    end = request.args.get("endDate")
    args = []
    if start: args += ["--start-date", start]
    if end: args += ["--end-date", end]
    return jsonify(run_script(SCRIPTS["bitcoin"], args))

# =========================================================
# 💎 Ethereum Endpoint
# =========================================================
@app.route("/api/eth")
def api_eth():
    start = request.args.get("startDate")
    end = request.args.get("endDate")
    args = []
    if start: args += ["--start-date", start]
    if end: args += ["--end-date", end]

    data = run_script(SCRIPTS["eth"], args)
    if not isinstance(data, dict):
        data = {"error": "ETH script returned invalid data"}

    # Default placeholders for missing keys
    data.setdefault("staking", [])
    data.setdefault("staking_flows", {"dates": [], "inflows": [], "outflows": [], "net": []})
    data.setdefault("stakers_change", {"dates": [], "values": []})
    data.setdefault("stakers_distribution", {"labels": [], "values": []})
    data.setdefault("insights", [])
    data.setdefault("analysis", "No analysis available.")
    data.setdefault("conclusion", "No conclusion available.")

    return jsonify(data)

# =========================================================
# 🧩 Binance Polar Endpoint
# =========================================================
@app.route("/api/binance_polar")
def api_binance_polar():
    return jsonify(run_script(SCRIPTS["binance_polar"]))

# =========================================================
# 🧠 MarketBrain (Allium)
# =========================================================
@app.route("/api/marketbrain")
def api_marketbrain():
    start = request.args.get("startDate")
    end = request.args.get("endDate")
    symbols = request.args.get("symbols") or request.args.get("symbol")
    range_param = request.args.get("range")
    today = datetime.utcnow().date()

    # Date range defaults
    if range_param and not (start and end):
        if range_param.endswith("W"):
            start = today - relativedelta(weeks=int(range_param[:-1]))
        elif range_param.endswith("M"):
            start = today - relativedelta(months=int(range_param[:-1]))
        elif range_param.endswith("Y"):
            start = today - relativedelta(years=int(range_param[:-1]))
        end = today.isoformat()
        start = start.isoformat()

    if not (start and end):
        start = (today - relativedelta(days=30)).isoformat()
        end = today.isoformat()

    args = ["--from", start, "--to", end]
    chains = [s.strip().upper() for s in (symbols or "ETH").replace(",", " ").split() if s.strip()]
    if len(chains) > 1:
        logger.warning(f"[MarketBrain] Multiple symbols requested ({chains}) → defaulting to ETH")
        chains = ["ETH"]
    for c in chains:
        args += ["--chains", c]
    args += ["--format", "json"]

    # ✅ Pass API keys to sub-scripts
    os.environ["ALLIUM_API_KEY"] = API_KEYS.get("ALLIUM_API_KEY", "") or ""
    os.environ["ALLIUM_QUERY_KEY"] = API_KEYS.get("ALLIUM_QUERY_KEY", "") or ""
    os.environ["ARKHAM_API_KEY"] = API_KEYS.get("ARKHAM_API_KEY", "") or ""

    raw = run_script(SCRIPTS["marketbrain"], args)

    try:
        data = raw if isinstance(raw, dict) else {}
        results = data.get("results", {})
        if not results:
            results = {}
            for sym, content in (data.get("analytics") or {}).items():
                results[sym] = {
                    "symbol": sym,
                    "insights": content.get("insights", ""),
                    "stats": content.get("stats", {}),
                    "arkham_summary": content.get("arkham_summary", {}),
                    "staking_table": content.get("staking_table", []),
                    "source": "allium",
                    "timestamp": content.get("timestamp"),
                }

        return jsonify({
            "results": results,
            "source": "allium",
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "marketbrain"
        })

    except Exception as e:
        logger.exception("[MarketBrain] Error:")
        return jsonify({"error": str(e), "raw": raw}), 500

# =========================================================
# 💰 Binance Market Endpoint (Smart Money Version)
# =========================================================
@app.route("/api/binance_market", methods=["GET"])
def api_binance_market():
    try:
        symbol = (request.args.get("symbol") or "BTC").upper().strip()
        start = request.args.get("startDate")
        end = request.args.get("endDate")

        if not (start and end):
            end = datetime.utcnow().strftime("%Y-%m-%d")
            start = (datetime.utcnow() - relativedelta(days=30)).strftime("%Y-%m-%d")

        # ✅ Usamos el script nuevo Smart Money + Accumulation
        script_path = os.path.join(os.path.dirname(__file__), "binance_market_fetcher.py")
        args = [symbol, "--start-date", start, "--end-date", end]

        logger.info(f"[Binance Market] Fetching data for {symbol} ({start} → {end})")

        output = run_script(script_path, args)

        if not output:
            return jsonify({"status": "error", "message": "No output from script"}), 500

        logger.info(f"[Binance Market] ✅ Data ready for {symbol}")

        # ✅ Respondemos directo, sin envolver en results{}
        return jsonify(output)

    except Exception as e:
        logger.exception(f"[Binance Market] Exception: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    


# =========================================================
# 📤 EXPORT CSV
# =========================================================
@app.route("/api/export_csv")
def export_csv():
    section = request.args.get("section")
    symbol = (request.args.get("symbol") or request.args.get("symbols") or "").upper()
    start = request.args.get("startDate")
    end = request.args.get("endDate")

    logger.info(f"[EXPORT CSV] Section={section} Symbol={symbol} Range={start}→{end}")

    # ✅ MarketBrain (Allium) CSV
    if section == "allium":
        script = SCRIPTS["marketbrain"]
        args = ["--from", start, "--to", end, "--chains", symbol, "--format", "csv"]
        output = run_script(script, args)
        return Response(output if isinstance(output, str) else json.dumps(output),
                        mimetype="text/csv")

    # ✅ Binance Market CSV — convertimos velas a tabla OHLC
    elif section == "binance_market":
        data = run_script(SCRIPTS["binance-market"], [symbol, "--start-date", start, "--end-date", end])

        candles = data.get("candles", {})
        if not candles or not candles.get("dates"):
            return jsonify({"error": "No market data available"}), 500

        # Convertir OHLC → CSV
        df = pd.DataFrame({
            "date": candles.get("dates", []),
            "open": candles.get("open", []),
            "high": candles.get("high", []),
            "low": candles.get("low", []),
            "close": candles.get("close", []),
        })

        csv_data = df.to_csv(index=False)
        return Response(csv_data, mimetype="text/csv")

    # ✅ Binance Polar CSV (simple)
    elif section == "binance_polar":
        script = SCRIPTS["binance_polar"]
        output = run_script(script, ["--format", "csv"])
        return Response(output if isinstance(output, str) else json.dumps(output),
                        mimetype="text/csv")

    return jsonify({"error": "Invalid section"}), 400

# =========================================================
# 📄 EXPORT PDF
# =========================================================
@app.route("/api/export_pdf")
def export_pdf():
    return {"error": "❌ PDF export via API is disabled. Use Electron export instead."}, 410

# =========================================================
# 🚀 Main
# =========================================================
if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 5001))
    logger.info(f"Starting WhaleScope Backend on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port)