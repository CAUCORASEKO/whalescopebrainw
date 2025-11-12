
#!/usr/bin/env python3
"""
analytics_loader.py
Manages the marketbrain.db database:
- Creates necessary tables
- Saves staking and whale detector data
- Allows manual initialization of the DB
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "marketbrain.db")

# ============================================================
# DB INIT
# ============================================================

def init_db():
    """Create the tables in marketbrain.db if they don't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS staking_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        activity_date TEXT,
        total_stake REAL,
        active_stake REAL,
        active_stake_usd_current REAL,
        pct_total_stake_active REAL,
        pct_circulating_staked_est REAL,
        token_price REAL,
        net_flow REAL,
        deposits_est REAL,
        withdrawals_est REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS whale_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timestamp TEXT,
        input_usd REAL,
        output_usd REAL,
        net_flow REAL,
        status TEXT,
        intensity INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized:", DB_PATH)

# ============================================================
# SAVE: staking_data
# ============================================================

def save_to_db(symbol: str, staking_table: list):
    """Save staking_data into SQLite (convert timestamps and remove duplicates)."""
    if not staking_table:
        print(f"[DB] No staking data to save for {symbol}")
        return

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for row in staking_table:
        date_value = row.get("activity_date")

        # 🔧 Normalize dates into SQLite-compatible string format
        if isinstance(date_value, pd.Timestamp):
            date_value = date_value.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(date_value, datetime):
            date_value = date_value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(date_value, (float, int)):
            # UNIX timestamp
            date_value = datetime.fromtimestamp(date_value).strftime("%Y-%m-%d %H:%M:%S")
        elif not isinstance(date_value, str):
            date_value = str(date_value)

        try:
            cur.execute("""
            INSERT OR REPLACE INTO staking_data (
                symbol, activity_date, total_stake, active_stake,
                active_stake_usd_current, pct_total_stake_active,
                pct_circulating_staked_est, token_price, net_flow,
                deposits_est, withdrawals_est
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                date_value,
                row.get("total_stake"),
                row.get("active_stake"),
                row.get("active_stake_usd_current"),
                row.get("pct_total_stake_active"),
                row.get("pct_circulating_staked_est"),
                row.get("token_price"),
                row.get("net_flow"),
                row.get("deposits_est"),
                row.get("withdrawals_est"),
            ))
        except Exception as e:
            print(f"[DB] ⚠️ Error inserting row for {symbol}: {e} ({type(date_value)}) -> {date_value}")

    conn.commit()
    conn.close()
    print(f"[DB] ✅ Saved staking data for {symbol}")

# ============================================================
# SAVE: whale_signals
# ============================================================

def save_whale_signals(symbol: str, signals: list):
    """Save whale detector signals into the database."""
    if not signals:
        print(f"[DB] No whale signals to save for {symbol}")
        return

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for s in signals:
        try:
            cur.execute("""
            INSERT INTO whale_signals (
                symbol, timestamp, input_usd, output_usd, net_flow, status, intensity
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                s.get("timestamp"),
                s.get("input_usd"),
                s.get("output_usd"),
                s.get("net_flow"),
                s.get("status"),
                s.get("intensity", 1),
            ))
        except Exception as e:
            print(f"[DB] ⚠️ Error inserting whale signal: {e}")

    conn.commit()
    conn.close()
    print(f"[DB] ✅ Saved {len(signals)} whale signals for {symbol}")

# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":
    init_db()
