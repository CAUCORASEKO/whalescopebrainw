#!/usr/bin/env python3
"""
Force insert Allium data into SQLite for MarketBrain.
"""

import os
import sqlite3
import json
import subprocess
from datetime import datetime

# Path to the database
DB_PATH = os.path.expanduser(
    "~/Desktop/whalescope-desktop/whalescope/python/whalescope_scripts/whalescope.db"
)

# SQL query for Allium data
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
    """Run staking_analysis.py to retrieve Allium data in JSON format."""
    cmd = [
        "python", "staking_analysis.py",
        "--queries", ALLIUM_QUERY,
        "--format", "json",
        "--api"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error executing staking_analysis.py")
        print(result.stderr)
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("results", [])
    except Exception as e:
        print("❌ Error parsing JSON:", e)
        print(result.stdout[:500])
        return []


def insert_into_sqlite(rows):
    """Insert Allium query results into whalescope.db."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
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
            print("⚠️ Error inserting row:", e, row)

    conn.commit()
    conn.close()
    print(f"✅ Inserted {inserted} new records into {DB_PATH}")


if __name__ == "__main__":
    print("🔎 Fetching data from Allium...")
    rows = fetch_allium()
    print(f"📊 Retrieved {len(rows)} records")
    if rows:
        insert_into_sqlite(rows)
