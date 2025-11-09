
# fetch_balance_data.py 

#!/usr/bin/env python3
# fetch_balance_data.py
# Query historical balances from whalescope.db for BlackRock entity

import sys
import sqlite3
import json
import logging
import pandas as pd
import argparse
import os
from datetime import datetime

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('fetch_balance_data.log')]
)

# DB path relative to project
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "..", "..", "whalescope.db")

def query_balances(start_date, end_date):
    """Query historical BTC/ETH balances from whalescope.db for BlackRock."""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT token, balance, balance_usd, timestamp
        FROM arkham_wallets
        WHERE entity_id = ? AND token IN ('BTC','ETH')
        AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn, params=('blackrock', start_date, end_date))
        conn.close()
        logging.info(f"Queried {len(df)} rows from {start_date} to {end_date}")
        return df
    except Exception as e:
        logging.error(f"Failed to query balances: {e}")
        return pd.DataFrame()

def format_data(df):
    """Format balance data as JSON (per token)."""
    if df.empty:
        return {'BTC': [], 'ETH': []}
    data = {}
    for token in df['token'].unique():
        token_df = df[df['token'] == token]
        data[token] = [
            {
                'timestamp': datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S").isoformat() + "Z",
                'balance': row['balance'],
                'balance_usd': row['balance_usd']
            }
            for _, row in token_df.iterrows()
        ]
    logging.info(f"Formatted data: { {k: len(v) for k,v in data.items()} }")
    return data

def main():
    logging.info("Starting fetch_balance_data.py")
    parser = argparse.ArgumentParser(description="Fetch BlackRock balance data")
    parser.add_argument('--start-date', type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument('--api', action='store_true', help="Output JSON only (skip file write)")
    args = parser.parse_args()

    try:
        start_ts = f"{args.start_date} 00:00:00"
        end_ts   = f"{args.end_date} 23:59:59"
        df = query_balances(start_ts, end_ts)
        data = format_data(df)

        if not args.api:
            out_file = 'blackrock_balances.json'
            with open(out_file, 'w') as f:
                json.dump(data, f, indent=4)
            logging.info(f"Saved balance data to {out_file}")

        print(json.dumps(data))  # Always print for IPC
        sys.stdout.flush()
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(json.dumps({'error': str(e)}))

if __name__ == "__main__":
    main()
