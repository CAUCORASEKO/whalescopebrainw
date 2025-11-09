#!/usr/bin/env python3
# ============================================================
# WhaleScope Whale Flow Detector (100% Datos Reales)
# ------------------------------------------------------------
# - Analiza inflows/outflows provenientes de Binance aggTrades
# - Detecta actividad de ballenas usando anomalías de volumen
# - Retorna eventos diarios con dirección del flujo (in/out)
# ============================================================

import pandas as pd
import numpy as np
import json

def detect_whale_flows(df: pd.DataFrame, symbol: str = "BTC", volume_multiplier: float = 2.0):
    """
    Detecta flujos de ballenas (whales) basados en anomalías de volumen.

    Parámetros
    ----------
    df : pd.DataFrame
        Debe tener columnas:
            ['date', 'close', 'inflow_usd', 'outflow_usd']
        donde:
            inflow_usd  = volumen total de compras (USDT)
            outflow_usd = volumen total de ventas (USDT)
    symbol : str
        Símbolo del activo (BTC, ETH, SOL, etc.)
    volume_multiplier : float
        Umbral de sensibilidad:
            - 2.0 = estándar (volumen > 2× promedio móvil)
            - 1.5 = más sensible (detecta más actividad)
            - 3.0 = más estricto (solo movimientos grandes)

    Retorna
    -------
    list[dict]
        Lista de eventos con:
            - timestamp
            - input_usd
            - output_usd
            - net_flow
            - status ("net_inflow" / "net_outflow")
            - symbol
    """

    # Validación básica
    required_cols = {"date", "inflow_usd", "outflow_usd"}
    if df.empty or not required_cols.issubset(df.columns):
        return []

    df = df.copy()
    df["net_flow"] = df["inflow_usd"] - df["outflow_usd"]
    df["volume"] = df["inflow_usd"] + df["outflow_usd"]

    # Promedio móvil (SMA) de 7 días para detectar anomalías
    df["sma_volume"] = df["volume"].rolling(window=7, min_periods=1).mean()

    # Día de ballena si el volumen supera N × promedio móvil
    df["whale_flag"] = df["volume"] > df["sma_volume"] * volume_multiplier

    whale_days = df[df["whale_flag"]]
    results = []

    for _, row in whale_days.iterrows():
        results.append({
            "timestamp": str(row["date"]),
            "input_usd": float(row["inflow_usd"]),
            "output_usd": float(row["outflow_usd"]),
            "net_flow": float(row["net_flow"]),
            "status": "net_inflow" if row["net_flow"] > 0 else "net_outflow",
            "symbol": symbol
        })

    return results


# ============================================================
# CLI (Modo independiente, sin datos ficticios)
# ============================================================
if __name__ == "__main__":
    """
    Si ejecutas este archivo directamente NO genera datos falsos.
    Solo imprime un aviso.
    Ejemplo de uso real:
        - desde binance_market_fetcher.py
        - recibe df con datos de Binance aggTrades reales
    """
    print("⚠️ Este script no genera datos por sí solo. "
          "Es utilizado por binance_market_fetcher.py con datos reales de Binance.")