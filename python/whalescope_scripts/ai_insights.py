# ai_insights.py — centraliza AI insights con cache
import os
import json
import hashlib
import time
from openai import OpenAI

CACHE_DIR = "cache_ai"
CACHE_DURATION = 3600  # 1 hora
os.makedirs(CACHE_DIR, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

def _get_cache_key(asset: str, params: dict):
    raw = asset + json.dumps(params, sort_keys=True)
    return os.path.join(CACHE_DIR, hashlib.md5(raw.encode()).hexdigest() + ".json")

def generate_ai_insights_from_cache(asset: str, **kwargs):
    """
    Genera insights de mercado usando GPT-4 pero con cache para no gastar tokens.
    - asset: "bitcoin" o "ethereum"
    - kwargs: price, percent_change_24h, net_flow, whale_tx, support_level, etc.
    """
    cache_file = _get_cache_key(asset, kwargs)

    # 1. Si existe cache y no expiró → devolver
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if time.time() - cached["timestamp"] < CACHE_DURATION:
                return cached["insight"]
        except Exception:
            pass

    # 2. Si no hay API key → devolver insight vacío
    if not client:
        return ""

    # 3. Generar prompt
    prompt = (
        f"Asset: {asset}\n"
        f"Price: {kwargs.get('price')}\n"
        f"24h: {kwargs.get('percent_change_24h')}%\n"
        f"7d: {kwargs.get('percent_change_7d')}%\n"
        f"30d: {kwargs.get('percent_change_30d')}%\n"
        f"Net Flow: {kwargs.get('net_flow')}\n"
        f"Whale Tx: {kwargs.get('whale_tx')}\n"
        f"Support Level: {kwargs.get('support_level')}\n\n"
        "➡️ Give a concise professional insight about the asset trends, "
        "whale activity, and possible scenarios."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a crypto market analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=250
        )
        insight_text = response.choices[0].message.content.strip()

        # 4. Guardar en cache
        with open(cache_file, "w") as f:
            json.dump({"timestamp": time.time(), "insight": insight_text}, f, indent=2)

        return insight_text
    except Exception as e:
        print(f"[AI Insights] Error: {e}")
        return ""