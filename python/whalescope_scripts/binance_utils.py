# --- NEW: Candlestick fetcher (Binance Klines) ---
import requests, time, hmac, hashlib

def fetch_binance_candlesticks(symbol="ETHUSDT", interval="1d", limit=100, api_key=None, api_secret=None):
    """Fetch candlestick data from Binance using signed request"""
    base_url = "https://api.binance.com"
    endpoint = "/api/v3/klines"

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }

    headers = {"X-MBX-APIKEY": api_key}

    try:
        resp = requests.get(base_url + endpoint, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        klines = resp.json()
        candles = []
        for k in klines:
            candles.append({
                "time": time.strftime("%Y-%m-%d", time.gmtime(k[0]/1000)),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4])
            })
        return candles
    except Exception as e:
        print(f"[Binance Klines] ⚠️ Error fetching {symbol}: {e}")
        return []