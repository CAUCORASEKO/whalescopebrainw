#!/usr/bin/env python3
"""
Force insert Allium data into SQLite for MarketBrain.
"""

import os
import sqlite3
import json
import subprocess
from datetime import datetime

# Ruta a la DB
DB_PATH = os.path.expanduser("~/Desktop/whalescope-desktop/whalescope/python/whalescope_scripts/whalescope.db")

# Query SQL que usaremos en Allium
ALLIUM_QUERY = """
SELECT
  activity_date,
  chain,
  active_addresses,
  total_transactions,
  transaction_fees_usd
FROM crosschain.metrics.overview
WHERE chain IN ('ethereum', 'solana', 'polygon', 'bnb', 'avalanche')
  AND activity_date >= DATEADD(month, -24, CURRENT_DATE())
ORDER BY activity_date, chain;
"""

def fetch_allium():
    """Ejecuta staking_analysis.py para traer datos de Allium en JSON"""
    cmd = [
        "python", "staking_analysis.py",
        "--queries", ALLIUM_QUERY,
        "--format", "json",
        "--api"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error ejecutando staking_analysis.py")
        print(result.stderr)
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("results", [])
    except Exception as e:
        print("❌ Error parseando JSON:", e)
        print(result.stdout[:500])
        return []

def insert_into_sqlite(rows):
    """Inserta los resultados en whalescope.db"""
    if not os.path.exists(DB_PATH):
        print(f"❌ No existe la DB en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    inserted = 0
    for row in rows:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO metrics
                (activity_date, chain, active_addresses, total_transactions, transaction_fees_usd)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["activity_date"],
                row["chain"],
                row["active_addresses"],
                row["total_transactions"],
                row["transaction_fees_usd"]
            ))
            inserted += 1
        except Exception as e:
            print("⚠️ Error insertando fila:", e, row)

    conn.commit()
    conn.close()
    print(f"✅ Insertados {inserted} registros nuevos en {DB_PATH}")

if __name__ == "__main__":
    print("🔎 Consultando Allium...")
    rows = fetch_allium()
    print(f"📊 {len(rows)} registros obtenidos")
    if rows:
        insert_into_sqlite(rows)