
# analytics.py

import pandas as pd
import sqlite3
import numpy as np
from sklearn.decomposition import PCA
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from datetime import datetime, timedelta
from allium_analytics import get_allium_metrics
import os 
import json

# ====== CONFIG ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crypto_data.db")




def main(start_date=None, end_date=None):
    end_date = end_date or datetime.utcnow().date()
    start_date = start_date or (end_date - timedelta(days=30))
    
    pca_result = perform_pca(start_date, end_date)
    regression_result = cross_sectional_regression(start_date, end_date)
    
   # 🔹 Integrates Allium data if the API is active
    try:
        allium_data = get_allium_metrics(protocol="binance-staking")
    except Exception as e:
        allium_data = {"status": "error", "message": str(e)}

    return {
        "pca": pca_result,
        "regression": regression_result,
        "allium": allium_data
    }



def perform_pca(start_date, end_date):
    """Perform PCA on staking data."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT date, symbol, price, volume, staking_ratio, market_cap FROM staking WHERE date BETWEEN ? AND ?"
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    conn.close()
    
    if df.empty:
        return {"error": "No data available"}
    
    # Prepare data for PCA
    features = ["price", "volume", "staking_ratio", "market_cap"]
    X = df.pivot(index="date", columns="symbol", values=features).fillna(0)
    X = X.values.reshape(X.shape[0], -1)
    
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(X)
    explained_variance = pca.explained_variance_ratio_
    
    return {
        "pca_explained_variance": explained_variance.tolist(),
        "pca_components": pca_result.tolist()
    }

def cross_sectional_regression(start_date, end_date):
    """Perform cross-sectional regression."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT date, symbol, price, staking_ratio, market_cap FROM staking WHERE date BETWEEN ? AND ?"
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    conn.close()
    
    if df.empty:
        return {"error": "No data available"}
    
    # Calculate returns
    df['returns'] = df.groupby('symbol')['price'].pct_change().shift(-1)
    df = df.dropna()
    
    X = df[["staking_ratio", "market_cap"]]
    X = add_constant(X)
    y = df["returns"]
    
    model = OLS(y, X).fit()
    return {
        "r_squared": model.rsquared,
        "coefficients": model.params.to_dict(),
        "summary": str(model.summary())
    }

def main(start_date=None, end_date=None):
    end_date = end_date or datetime.utcnow().date()
    start_date = start_date or (end_date - timedelta(days=30))
    
    pca_result = perform_pca(start_date, end_date)
    regression_result = cross_sectional_regression(start_date, end_date)
    
    return {
        "pca": pca_result,
        "regression": regression_result
    }

if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))