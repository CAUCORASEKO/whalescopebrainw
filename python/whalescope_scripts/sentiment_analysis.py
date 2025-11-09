# sentiment_analysis.py

import requests
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import json

load_dotenv()

# ====== CONFIG ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crypto_data.db")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY")
SYMBOLS = [
    "BTC", "ETH", "SOL", "ADA", "BNB", "AVAX", "TRX", "DOT", "MATIC", "NEAR",
    "ATOM", "XRP", "LINK", "LTC", "DOGE"
]

def init_sentiment_db():
    """Initialize sentiment table."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sentiment (
            date TEXT,
            symbol TEXT,
            sentiment_score REAL,
            social_volume REAL,
            PRIMARY KEY (date, symbol)
        )
    """)
    conn.commit()
    conn.close()

def fetch_sentiment(symbol, start_date, end_date):
    """Fetch sentiment data from LunarCrush."""
    url = f"https://api.lunarcrush.com/v2/coin/{symbol.lower()}"
    headers = {"Authorization": f"Bearer {LUNARCRUSH_API_KEY}"}
    params = {
        "start": int(start_date.timestamp()),
        "end": int(end_date.timestamp()),
        "timeframe": "1w"  # Weekly data
    }
    try:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        return [
            {
                "date": datetime.fromtimestamp(record["time"]).strftime("%Y-%m-%d"),
                "sentiment_score": record.get("sentiment", 0),
                "social_volume": record.get("social_volume", 0)
            }
            for record in data.get("time_series", [])
        ]
    except Exception as e:
        print(f"Error fetching sentiment for {symbol}: {e}")
        return []

def main(start_date=None, end_date=None):
    init_sentiment_db()
    end_date = end_date or datetime.utcnow().date()
    start_date = start_date or (end_date - timedelta(days=30))
    results = []

    for symbol in SYMBOLS:
        sentiment_data = fetch_sentiment(symbol, start_date, end_date)
        for record in sentiment_data:
            results.append({
                "date": record["date"],
                "symbol": symbol,
                "sentiment_score": record["sentiment_score"],
                "social_volume": record["social_volume"]
            })
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT OR REPLACE INTO sentiment (date, symbol, sentiment_score, social_volume)
                VALUES (?, ?, ?, ?)
            """, (
                record["date"], symbol, record["sentiment_score"], record["social_volume"]
            ))
            conn.commit()
            conn.close()
    
    return results

if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))