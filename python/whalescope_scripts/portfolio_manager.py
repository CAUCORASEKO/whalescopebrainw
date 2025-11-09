# portfolio_manager.py

import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import os

# ====== CONFIG ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crypto_data.db")

def sort_portfolio(criteria="momentum", start_date=None, end_date=None, top_n=5):
    """Sort portfolio based on criteria (SMB, HML, momentum)."""
    conn = sqlite3.connect(DB_PATH)
    end_date = end_date or datetime.utcnow().date()
    start_date = start_date or (end_date - timedelta(days=30))
    
    query = """
        SELECT symbol, date, price, market_cap, volume
        FROM staking
        WHERE date BETWEEN ? AND ?
    """
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    conn.close()
    
    if df.empty:
        return []
    
    # Calculate returns
    df['returns'] = df.groupby('symbol')['price'].pct_change().shift(-1)
    
    # Sort based on criteria
    if criteria == "momentum":
        ranked = df.groupby('symbol')['returns'].mean().sort_values(ascending=False)
    elif criteria == "SMB":  # Small Minus Big (small market cap)
        ranked = df.groupby('symbol')['market_cap'].mean().sort_values(ascending=True)
    elif criteria == "HML":  # High Minus Low (high book-to-market, approximated by low price)
        ranked = df.groupby('symbol')['price'].mean().sort_values(ascending=True)
    
    top_symbols = ranked.head(top_n).index.tolist()
    return top_symbols

def rebalance_portfolio(portfolio, weights=None, rebalance_date=None):
    """Simulate portfolio rebalancing."""
    weights = weights or {symbol: 1/len(portfolio) for symbol in portfolio}
    rebalance_date = rebalance_date or datetime.utcnow().date()
    
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT symbol, price FROM staking WHERE date = ? AND symbol IN ({})".format(
        ",".join(["?"] * len(portfolio))
    )
    df = pd.read_sql_query(query, conn, params=[rebalance_date.isoformat()] + portfolio)
    conn.close()
    
    portfolio_value = sum(df[df['symbol'] == symbol]['price'].iloc[0] * weights.get(symbol, 0) 
                         for symbol in portfolio if symbol in df['symbol'].values)
    
    return {
        "portfolio": portfolio,
        "weights": weights,
        "value": portfolio_value,
        "date": rebalance_date.isoformat()
    }

if __name__ == "__main__":
    # Example: Sort portfolio by momentum
    portfolio = sort_portfolio(criteria="momentum", top_n=5)
    print("Selected portfolio:", portfolio)
    
    # Rebalance portfolio
    weights = {symbol: 0.2 for symbol in portfolio}  # Equal weights
    result = rebalance_portfolio(portfolio, weights)
    print("Rebalanced portfolio:", result)