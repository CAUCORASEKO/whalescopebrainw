#!/usr/bin/env python3
import json
import requests
import os

API_KEYS_FILE = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")

def load_keys():
    try:
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

API_KEYS = load_keys()
CMC_API_KEY = API_KEYS.get("CMC_API_KEY")

def get_token_fundamentals(symbol):
    """
    Returns: market_cap, fdv, current_supply, max_supply, or None on failure.
    """
    if not CMC_API_KEY:
        print("⚠️ No CMC API key found")
        return None

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol.upper()}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()

        d = data["data"][symbol.upper()]
        usd = d["quote"]["USD"]

        return {
            "market_cap": usd.get("market_cap"),
            "fdv": usd.get("fully_diluted_market_cap"),
            "current_supply": d.get("circulating_supply"),
            "max_supply": d.get("max_supply"),
        }

    except Exception as e:
        print(f"[CMC] Error: {e}")
        return None