#!/usr/bin/env python3
"""
whale_detector.py
Detecta actividad de ballenas estilo Whalemap usando datos públicos de Binance.
Autor: MarketBrain Labs
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# ============================================================
# Descarga de datos desde Binance (API pública)
# ============================================================

def fetch_binance_klines(symbol: str = "ETHUSDT", interval: str = "1d", days: int = 90):
    """
    Descarga klines (velas OHLCV) desde la API pública de Binance.
    symbol: e.g. "ETHUSDT"
    interval: "1d", "4h", "1h", etc.
    days: número de días hacia atrás.
    """
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time,
        "limit": 1000
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close",
            "volume", "close_time", "quote_asset_volume",
            "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["dates"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["symbol"] = symbol
        return df[["dates", "close", "volume", "symbol"]]
    except Exception as e:
        print(f"[BINANCE] Error fetching klines for {symbol}: {e}")
        return pd.DataFrame()

# ============================================================
# WHALE DETECTOR - estilo Whalemap
# ============================================================

def detect_whale_flows(df: pd.DataFrame, symbol: str = "ETH", lookback: int = 7):
    """
    Detecta actividad de ballenas basándose en spikes de volumen.
    Devuelve lista con estructura: [{timestamp, input_usd, output_usd, net_flow, status, symbol}]
    """
    if df.empty or "volume" not in df.columns or "close" not in df.columns:
        return []

    df = df.copy()
    df["sma_volume"] = df["volume"].rolling(window=lookback, min_periods=1).mean()

    # Flags de intensidad (tipo Whalemap)
    df["f1"] = df["volume"] > df["sma_volume"] * 2.00
    df["f2"] = df["volume"] > df["sma_volume"] * 1.75
    df["f3"] = df["volume"] > df["sma_volume"] * 1.50
    df["f4"] = df["volume"] > df["sma_volume"] * 1.25
    df["f5"] = df["volume"] > df["sma_volume"] * 1.00

    df["buyer_vol"] = np.where(df["close"] > df["close"].shift(1), df["volume"], 0)
    df["seller_vol"] = np.where(df["close"] < df["close"].shift(1), df["volume"], 0)

    signals = []
    for _, row in df.iterrows():
        size = 0
        if row["f1"]:
            size = 5
        elif row["f2"]:
            size = 4
        elif row["f3"]:
            size = 3
        elif row["f4"]:
            size = 2
        elif row["f5"]:
            size = 1

        if size > 0:
            side = "buy" if row["buyer_vol"] > row["seller_vol"] else "sell"
            signals.append({
                "timestamp": str(row["dates"]),
                "input_usd": float(row["volume"]) if side == "buy" else 0,
                "output_usd": float(row["volume"]) if side == "sell" else 0,
                "net_flow": float(row["volume"]) if side == "buy" else -float(row["volume"]),
                "status": side,
                "symbol": symbol,
                "intensity": size
            })

    return signals

# ============================================================
# Ejemplo de uso
# ============================================================

if __name__ == "__main__":
    df = fetch_binance_klines("ETHUSDT", interval="1d", days=60)
    whales = detect_whale_flows(df, "ETH")
    print(f"Detected {len(whales)} whale signals for ETH in last 60 days.")
    if whales:
        print(whales[:5])