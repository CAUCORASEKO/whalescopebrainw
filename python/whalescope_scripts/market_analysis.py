# market_analysis.py
# Funciones comunes para generar análisis de mercado (BTC, ETH, etc.)

import pandas as pd

def generate_trading_advice(price, change_24h, net_flow, whale_tx, support_level, df: pd.DataFrame, asset="BTC"):
    """
    Genera un análisis de mercado basado en métricas de corto y mediano plazo.

    Parámetros
    ----------
    price : float
        Precio actual del activo.
    change_24h : float
        Cambio porcentual en 24h.
    net_flow : float
        Flujos netos de exchange (inflows - outflows).
    whale_tx : float
        Magnitud en USD de la mayor transacción/actividad de ballena detectada.
    support_level : float
        Nivel de soporte técnico (mínimo reciente).
    df : pd.DataFrame
        DataFrame con histórico de precios (columnas: ["close", "volume", ...]).
    asset : str
        Símbolo del activo (ejemplo: "BTC", "ETH").

    Retorna
    -------
    str
        Texto con el análisis resumido.
    """

    analysis = []

    # --- Corto plazo ---
    if change_24h < 0:
        analysis.append(f"Price declining ({change_24h:.2f}% in 24h)")
    else:
        analysis.append(f"Price rising ({change_24h:.2f}% in 24h)")

    # --- Flujos ---
    unit = asset.upper()
    if net_flow < 0:
        analysis.append(f"Negative net flow ({net_flow:.2f} {unit}) suggests accumulation")
    else:
        analysis.append(f"Positive net flow ({net_flow:.2f} {unit}) indicates potential selling")

    # --- Ballenas ---
    if whale_tx > 200e6:  # 200M USD
        analysis.append(f"High whale activity (${whale_tx/1e6:.1f}M): expect volatility")

    # --- Soporte ---
    if support_level and price <= support_level * 1.02:
        analysis.append(f"Price near support (${support_level:.0f}): potential rebound zone")

    # --- Tendencias de 7d y 30d + Volatilidad ---
    if not df.empty:
        last30 = df["close"].tail(30)
        if len(last30) >= 7:
            weekly_change = (last30.iloc[-1] - last30.iloc[-7]) / last30.iloc[-7] * 100
            monthly_change = (last30.iloc[-1] - last30.iloc[0]) / last30.iloc[0] * 100
            analysis.append(f"7d trend: {weekly_change:.2f}% | 30d trend: {monthly_change:.2f}%")

        vol = df["close"].tail(7).pct_change().std() * 100
        analysis.append(f"7d volatility: {vol:.2f}%")

    return " — ".join(analysis)
