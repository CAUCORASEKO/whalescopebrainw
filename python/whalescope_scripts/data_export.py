
# data_export.py

import sqlite3
import pandas as pd
import os
from datetime import datetime

# ====== CONFIG ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crypto_data.db")

def export_to_csv(filters=None):
    """Export data from SQLite to CSV with optional filters."""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM staking WHERE 1=1"
    params = []
    
    if filters:
        if "symbols" in filters and filters["symbols"]:
            query += " AND symbol IN ({})".format(",".join(["?"] * len(filters["symbols"])))
            params.extend(filters["symbols"])
        if "start_date" in filters:
            query += " AND date >= ?"
            params.append(filters["start_date"])
        if "end_date" in filters:
            query += " AND date <= ?"
            params.append(filters["end_date"])
        if "market_cap_min" in filters:
            query += " AND market_cap >= ?"
            params.append(filters["market_cap_min"])
        if "volume_min" in filters:
            query += " AND volume >= ?"
            params.append(filters["volume_min"])
        if "exchanges" in filters and filters["exchanges"]:
            query += " AND exchange IN ({})".format(",".join(["?"] * len(filters["exchanges"])))
            params.extend(filters["exchanges"])
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        print("No data found for the specified filters")
        return None
    
    output_path = f"marketbrain_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_path, index=False)
    print(f"Data exported to {output_path}")
    return output_path

if __name__ == "__main__":
    # Example usage
    filters = {
        "symbols": ["ETH", "BTC"],
        "start_date": "2025-08-01",
        "end_date": "2025-08-28",
        "market_cap_min": 1000000000,
        "volume_min": 500000,
        "exchanges": ["binance", "coinbase"]
    }
    export_to_csv(filters)