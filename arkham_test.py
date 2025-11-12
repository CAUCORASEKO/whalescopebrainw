import os
import json
import argparse
import requests


def load_api_key():
    """Load the ARKHAM_API_KEY from api_keys.json"""
    json_path = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"❌ File not found: {json_path}")
    with open(json_path, "r") as f:
        data = json.load(f)
        key = data.get("ARKHAM_API_KEY")
        if not key:
            raise ValueError("❌ ARKHAM_API_KEY not found in api_keys.json")
        return key


parser = argparse.ArgumentParser(description="Fetch token data from Arkham Intelligence API")
parser.add_argument("--symbol", type=str, default="ETH", help="Token symbol (default: ETH)")
args = parser.parse_args()

symbol = args.symbol.upper()
api_key = load_api_key()

headers = {"accept": "application/json", "x-api-key": api_key}

print(f"🔑 Using ARKHAM_API_KEY: {api_key[:8]}...")
print(f"🚀 Querying Arkham Intelligence for {symbol}...\n")

# === 1️⃣ Token Info ===
url_info = "https://api.arkhamintelligence.com/intelligence/token-entity"
resp_info = requests.get(url_info, headers=headers, params={"symbol": symbol})
print(f"[Token Info] Status: {resp_info.status_code}")
try:
    data = resp_info.json()
    print(json.dumps(data, indent=2)[:600])
except Exception:
    print(resp_info.text)

print("\n" + "=" * 80 + "\n")

# === 2️⃣ Holders Info ===
url_holders = f"https://api.arkhamintelligence.com/token/{symbol}/holders"
resp_hold = requests.get(url_holders, headers=headers)
print(f"[Token Holders] Status: {resp_hold.status_code}")
try:
    data = resp_hold.json()
    print(json.dumps(data, indent=2)[:800])
except Exception:
    print(resp_hold.text)
