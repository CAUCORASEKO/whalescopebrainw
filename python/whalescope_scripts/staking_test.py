import os, sys, requests, json
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
load_dotenv(os.path.join(HERE, ".env"))

STAKINGREWARDS_API_KEY = os.getenv("STAKINGREWARDS_API_KEY")

query = """
query {
  assets(where: { symbols: ["ETH"] }, limit: 1) {
    symbol
    metrics(limit: 5) {
      metricKey
      defaultValue
      createdAt
    }
  }
}
"""

headers = {
    "Content-Type": "application/json",
    "X-API-KEY": STAKINGREWARDS_API_KEY
}

try:
    r = requests.post(
        "https://api.stakingrewards.com/public/query",
        json={"query": query},
        headers=headers,
        timeout=20
    )
    print("Status:", r.status_code)
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print("Error:", e)
