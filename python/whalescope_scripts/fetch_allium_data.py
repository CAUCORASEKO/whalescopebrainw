#!/usr/bin/env python3
"""
fetch_allium_data.py
Automatically updates staking_data and whale_signals in marketbrain.db
and leaves an execution log in fetch_allium.log

"""

import subprocess
import datetime
import sqlite3
import sys
from pathlib import Path

# ===============================================
# 🧩 CONFIGURACIÓN
# ===============================================
CHAINS = ["solana", "ethereum", "polygon", "avalanche"]
BASE_PATH = Path("/Users/cauco/Desktop/whalescope-desktop/whalescope/python/whalescope_scripts")
DB_PATH = BASE_PATH / "marketbrain.db"
LOG_PATH = BASE_PATH / "fetch_allium.log"


# ===============================================
# 🪵 UTILIDAD DE LOGGING
# ===============================================
def log(msg: str):
    """Writes message to console and log file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ===============================================
# ⚙️ FUNCIONES PRINCIPALES
# ===============================================
def run_cmd(args):
    """Execute an external command and display output"""
    log(f"Executing command: {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"⚠️ Error executing {' '.join(args)}:\n{result.stderr}")
    else:
        log(f"✅ Command completed successfully.")
    return result.returncode == 0


def get_db_status():
    """Gets more recent dates from staking_data"""
    if not DB_PATH.exists():
        log("⚠️ Database not found, everything will be downloaded from scratch.")
        return [{"chain": c, "end_date": "2023-01-01"} for c in CHAINS]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = []
    for chain in CHAINS:
        try:
            q = f"""
            SELECT '{chain}' AS chain,
                   MIN(activity_date) AS start_date,
                   MAX(activity_date) AS end_date,
                   COUNT(*) AS records
            FROM staking_data
            WHERE LOWER(symbol) LIKE '%{chain[:3]}%';
            """
            cur.execute(q)
            data = cur.fetchone()
            rows.append({
                "chain": chain,
                "start_date": data[1] if data and data[1] else None,
                "end_date": data[2] if data and data[2] else None,
                "records": data[3] if data else 0
            })
        except Exception as e:
            log(f"⚠️ Error leyendo {chain}: {e}")
    conn.close()
    return rows


def fetch_chain(chain, start_date, end_date):
    """Download and update staking_data"""
    log(f"🔎 Fetching {chain} desde {start_date} hasta {end_date}...")
    args = [
        "python", "staking_analysis.py",
        "--chains", chain,
        "--from", start_date,
        "--to", end_date,
        "--format", "json"
    ]
    run_cmd(args)


def update_whales():
    """Run whales_detector.py to update whale_signals"""
    log("🐋 Updating whale signals...")
    args = ["python", "whales_detector.py"]
    run_cmd(args)
    log("✅ whale_signals updated.")


# ===============================================
# 🚀 ENTRYPOINT
# ===============================================
def main():
    log("🔄 --- EJECUCIÓN INICIADA ---")
    update_whales_flag = "--update-whales" in sys.argv
    db_status = get_db_status()
    today = datetime.date.today().isoformat()

    for entry in db_status:
        chain = entry["chain"]
        end_date = entry["end_date"][:10] if entry.get("end_date") else "2023-01-01"
        next_day = (datetime.date.fromisoformat(end_date) + datetime.timedelta(days=1)).isoformat()

        log(f"📊 {chain}: last date {end_date}, bringing from {next_day} until {today}")
        fetch_chain(chain, next_day, today)

    if update_whales_flag:
        update_whales()

    log("✅ Update complete. Run MarketBrain Dashboard again.")
    log("🔚 --- END OF EXECUTION ---\n")


if __name__ == "__main__":
    main()