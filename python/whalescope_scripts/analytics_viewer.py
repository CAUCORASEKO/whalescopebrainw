# analytics_viewer.py
import sys
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/Library/Application Support/whalescope/db/marketbrain.db"))

def load_symbol_data(symbol):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT activity_date, active_stake_usd_current, pct_total_stake_active, token_price "
        "FROM staking_data WHERE symbol = ? ORDER BY activity_date ASC",
        conn,
        params=(symbol,)
    )
    conn.close()
    return df

def plot_symbol(symbol):
    df = load_symbol_data(symbol)
    if df.empty:
        print(f"⚠️ No data found for {symbol}")
        return

    # Aseguramos que las fechas se interpreten correctamente
    df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")

    plt.figure(figsize=(10, 5))
    plt.plot(df["activity_date"], df["active_stake_usd_current"], label="Active Stake (USD)", color="cyan")
    
    if "token_price" in df.columns and df["token_price"].notna().any():
        ax2 = plt.twinx()
        ax2.plot(df["activity_date"], df["token_price"], label="Token Price (USD)", color="orange", alpha=0.7)
        ax2.set_ylabel("Token Price (USD)")
        ax2.legend(loc="upper right")
    else:
        print(f"⚠️ No price data for {symbol}")

    plt.title(f"Staking Overview — {symbol}")
    plt.xlabel("Date")
    plt.ylabel("Active Stake (USD)")
    plt.grid(True)
    plt.legend(loc="upper left")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    else:
        symbol = "TON"  # default

    plot_symbol(symbol)