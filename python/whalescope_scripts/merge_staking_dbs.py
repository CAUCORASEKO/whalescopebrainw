#!/usr/bin/env python3
# ============================================================
# WhaleScope | Merge ETH staking data into MarketBrain (Safe Write)
# merge_staking_dbs.py
# ============================================================

import sqlite3
import pandas as pd
from pathlib import Path
import time
import sys
from datetime import datetime


def log(msg):
    """Log messages safely to stderr (won’t break JSON output)."""
    ts = datetime.utcnow().strftime("[%H:%M:%S]")
    sys.stderr.write(f"{ts} {msg}\n")
    sys.stderr.flush()


def merge_eth_staking(retries=3, delay=1.5):
    """Merge ETH data from whalescope.db and electron/whalescope.db into marketbrain.db safely."""
    log("🔗 Connecting to databases...")

    base = Path("/Users/cauco/Desktop/whalescope-desktop/whalescope")
    db_main = base / "marketbrain.db"
    db_whalescope = base / "whalescope.db"
    db_electron = base / "electron/whalescope.db"

    # --- Conexiones de lectura ---
    try:
        conn_wscope = sqlite3.connect(db_whalescope)
        conn_elec = sqlite3.connect(db_electron)
    except Exception as e:
        log(f"❌ Database connection error: {e}")
        return

    try:
        df_eth_activity = pd.read_sql("SELECT * FROM eth_activity", conn_wscope)
        df_eth_ratio = pd.read_sql("SELECT * FROM eth_staking_ratio", conn_elec)
    except Exception as e:
        log(f"❌ Error leyendo datos ETH: {e}")
        conn_wscope.close()
        conn_elec.close()
        return

    # --- Normalización ---
    df_eth_ratio.columns = ["activity_date", "staking_ratio", "deposit_rate", "timestamp"]
    df_eth_ratio["symbol"] = "ETH"
    df_eth_ratio["chain_raw"] = "ethereum"

    df_eth_activity["symbol"] = "ETH"
    df_eth_activity["chain_raw"] = "ethereum"

    # --- Intentar grabar con reintentos ---
    for attempt in range(1, retries + 1):
        try:
            conn_main = sqlite3.connect(db_main, timeout=10)
            conn_main.execute("BEGIN IMMEDIATE;")  # Bloqueo de escritura
            log(f"💾 Writing ETH data (attempt {attempt}/{retries})...")

            conn_main.execute("DROP TABLE IF EXISTS staking_activity;")
            df_eth_activity.to_sql("staking_activity", conn_main, if_exists="replace", index=False)

            conn_main.execute("DROP TABLE IF EXISTS staking_eth_ratio;")
            df_eth_ratio.to_sql("staking_eth_ratio", conn_main, if_exists="replace", index=False)

            conn_main.commit()
            conn_main.close()
            log("✅ Merge complete: ETH data unified into marketbrain.db")
            break

        except sqlite3.OperationalError as e:
            log(f"⚠️ SQLite busy or locked (attempt {attempt}): {e}")
            time.sleep(delay)
            if attempt == retries:
                log("❌ Failed to write after several attempts — skipping merge.")
        finally:
            try:
                conn_main.close()
            except Exception:
                pass

    conn_wscope.close()
    conn_elec.close()


if __name__ == "__main__":
    merge_eth_staking()