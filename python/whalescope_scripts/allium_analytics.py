# allium_analytics.py

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ALLIUM_API_KEY = os.getenv("ALLIUM_API_KEY")
BASE_URL = "https://api.allium.so/api/v1"  # 👈 Ajustar si tu endpoint difiere

def get_allium_metrics(protocol="binance-staking", limit=100):
    """Obtiene métricas de Allium (por ejemplo TVL, yields o flujos on-chain)."""
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
    Wrapper para ejecución desde Flask backend.
    Ignora las fechas (por ahora) y devuelve métricas Allium en JSON.
    """
    try:
        # Ejecuta la función principal
        result = get_allium_metrics(protocol="binance-staking", limit=100)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}



def list_allium_protocols():
    """Devuelve la lista completa de protocolos disponibles en Allium"""
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