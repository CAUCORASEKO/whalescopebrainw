# allium_analytics.py

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ALLIUM_API_KEY = os.getenv("ALLIUM_API_KEY")
BASE_URL = "https://api.allium.so/api/v1"  # 👈 Adjust if your endpoint differs


def get_allium_metrics(protocol="binance-staking", limit=100):
    """Fetch Allium metrics (e.g., TVL, yields, or on-chain flows)."""
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ALLIUM_API_KEY}"
    }

    url = f"{BASE_URL}/protocols/{protocol}/metrics?limit={limit}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "ok",
            "protocol": protocol,
            "count": len(data.get("data", [])),
            "metrics": data.get("data", [])
        }
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# =========================================================
# Entry point for backend_ultra_pro integration
# =========================================================

def main(start_date=None, end_date=None):
    """
    Wrapper for execution from the Flask backend.
    Currently ignores start/end dates and returns Allium metrics as JSON.
    """
    try:
        # Execute the main function
        result = get_allium_metrics(protocol="binance-staking", limit=100)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def list_allium_protocols():
    """Return the full list of available protocols from Allium."""
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ALLIUM_API_KEY}"
    }
    url = f"{BASE_URL}/protocols"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print(json.dumps(get_allium_metrics(), indent=2))
