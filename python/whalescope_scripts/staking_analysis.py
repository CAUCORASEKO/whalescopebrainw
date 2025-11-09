#!/usr/bin/env python3
"""
staking_analysis.py
MarketBrain Ultimate — Allium + CoinGecko + Arkham + Whale Detector + DB

✅ Allium: staking + flows overview (principal fuente)
✅ CoinGecko: precios y fallback para métricas USD
✅ Arkham: whale inflows/outflows
✅ Binance: Whale detector (volumen anómalo)
✅ SQLite: persistencia de datos (marketbrain.db)
✅ OpenAI (opcional): insights automáticos
✅ Cache local (--no-cache, --no-insights)
"""

import os
import sys
import json
import argparse
import statistics
import hashlib
import pathlib
import math
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import sqlite3
import requests
from dotenv import load_dotenv

# 🔹 Importar módulos locales
from whale_detector import fetch_binance_klines, detect_whale_flows
from analytics_loader import save_to_db, save_whale_signals
from merge_staking_dbs import merge_eth_staking



# ===== Load API keys from Electron config =====
import json
CONFIG_PATH = os.path.expanduser("~/Library/Application Support/whalescope/api_keys.json")

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            keys = json.load(f)
        for k, v in keys.items():
            if v:
                os.environ[k] = v
    except Exception as e:
        print(f"[WARN] Could not load API keys: {e}")


# ============================================================
# Logging
# ============================================================

def log(*args, **kwargs):
    prefix = f"[{datetime.now().strftime('%H:%M:%S')}]"
    print(prefix, *args, file=sys.stderr, **kwargs)


# ============================================================
# Configuración
# ============================================================

CHAIN_MAP = {
    "eth": "ETH", "ethereum": "ETH",
    "sol": "SOL", "solana": "SOL",
    "matic": "MATIC", "polygon": "MATIC", "pol": "MATIC",
    "apt": "APTOS", "aptos": "APTOS",
    "bsc": "BSC", "bnb": "BSC", "binance": "BSC",
    "near": "NEAR", "sui": "SUI",
    "ton": "TON", "toncoin": "TON", "the-open-network": "TON",
}

ALLIUM_QUERIES = {
    "MULTI": "AcUpz2e1YbQtkOkM1BHG",  # único query multi-chain
}

CACHE_DIR = pathlib.Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# Cache
# ============================================================

def cache_get(symbol, start, end):
    key = hashlib.sha1(f"{symbol}-{start}-{end}".encode()).hexdigest()
    path = CACHE_DIR / f"{symbol}_{key}.json"
    if path.exists():
        try:
            log(f"[CACHE] Loading {path.name}")
            return json.load(open(path))
        except Exception:
            pass
    return None


def cache_set(symbol, start, end, data):
    key = hashlib.sha1(f"{symbol}-{start}-{end}".encode()).hexdigest()
    path = CACHE_DIR / f"{symbol}_{key}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log(f"[CACHE] Saved {path.name}")


def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


# ============================================================
# API Integrations
# ============================================================

def fetch_arkham_flows(symbol, start_date=None, end_date=None):
    """
    Fetch Arkham flows (tries both api.arkm.com and intel.arkm.com for Intel users)
    """
    import json, requests

    api_key = os.getenv("ARKHAM_API_KEY")
    if not api_key:
        log("[ARKHAM] ❌ Missing ARKHAM_API_KEY")
        return [{"error": "missing_api_key"}]

    headers = {"API-Key": api_key}
    params = {"timeLast": "30d"}
    candidates = [
        f"https://api.arkm.com/v1/token/top_flow/{symbol.lower()}",
        f"https://intel.arkm.com/api/token/top_flow/{symbol.lower()}",
    ]

    for url in candidates:
        try:
            log(f"[ARKHAM] 🔎 Trying {url}")
            resp = requests.get(url, headers=headers, params=params, timeout=20)

            if resp.status_code == 404 or resp.status_code == 401:
                log(f"[ARKHAM] {url} → {resp.status_code}")
                continue

            data = resp.json()
            if isinstance(data, list):
                inflow = sum(d.get("flowUSD", 0) for d in data if d.get("direction") == "in")
                outflow = sum(d.get("flowUSD", 0) for d in data if d.get("direction") == "out")
                return [{
                    "symbol": symbol.upper(),
                    "total_inflow": inflow,
                    "total_outflow": outflow,
                    "netflow": inflow - outflow,
                    "source": url.split("/")[2],
                    "raw_count": len(data)
                }]
        except Exception as e:
            log(f"[ARKHAM] ⚠️ Error with {url}: {e}")
            continue

    return [{"unsupported": True, "symbol": symbol.upper()}]

def fetch_coingecko_market(symbol):
    api_key = os.getenv("COINGECKO_API_KEY")
    cg_ids = {
        "ETH": "ethereum", "SOL": "solana", "MATIC": "matic-network",
        "APTOS": "aptos", "BSC": "binancecoin", "NEAR": "near",
        "SUI": "sui", "TON": "toncoin"
    }
    cg_id = cg_ids.get(symbol.upper())
    if not cg_id:
        return {}
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-cg-pro-api-key"] = api_key
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {}
        j = resp.json().get("market_data", {})
        return {
            "price_usd": j.get("current_price", {}).get("usd"),
            "market_cap_usd": j.get("market_cap", {}).get("usd"),
            "volume_24h": j.get("total_volume", {}).get("usd"),
            "circulating_supply": j.get("circulating_supply"),
            "price_change_24h": j.get("price_change_percentage_24h"),
        }
    except Exception:
        return {}


# ============================================================
# Allium
# ============================================================

def normalize_symbol(symbol: str) -> str:
    return CHAIN_MAP.get(symbol.lower(), symbol.upper())


def fetch_allium_staking(symbol: str, start_date: str, end_date: str):
    """
    Ejecuta el query Allium Multi-chain.
    El query no acepta parámetros, así que los omitimos.
    Luego se filtra por símbolo dentro de process_allium_staking().
    """
    api_key = os.getenv("ALLIUM_API_KEY")
    if not api_key:
        raise ValueError("Missing ALLIUM_API_KEY in environment")

    query_id = ALLIUM_QUERIES["MULTI"]
    base_url = "https://api.allium.so/api/v1/explorer"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    log(f"[ALLIUM] Running query {query_id} for {symbol} ({start_date} → {end_date})")

    try:
        run_url = f"{base_url}/queries/{query_id}/run-async"
        # ⚠️ El query no acepta parámetros, así que enviamos un payload vacío
        payload = {
            "parameters": {},
            "run_config": {"limit": 10000},
        }

        run_resp = requests.post(run_url, headers=headers, json=payload, timeout=60)
        run_resp.raise_for_status()
        run_id = run_resp.json().get("id") or run_resp.json().get("run_id")

        if not run_id:
            log(f"[ALLIUM] No run_id returned for {symbol}")
            return []

        # 🔁 Poll de estado
        poll_url = f"{base_url}/query-runs/{run_id}"
        for _ in range(60):
            poll = requests.get(poll_url, headers=headers, timeout=30).json()
            status = poll.get("status", "").lower()
            if status in ("success", "completed", "done"):
                break
            elif status in ("failed", "error"):
                log(f"[ALLIUM] Query failed for {symbol}")
                return []
            time.sleep(2)

        results = requests.get(f"{poll_url}/results", headers=headers, timeout=60).json()
        return results.get("data", [])
    except Exception as e:
        log(f"[ALLIUM] Error fetching {symbol}: {e}")
        return []


def process_allium_staking(symbol, data, start_date=None, end_date=None, market_data=None):
    import pandas as pd

    df = pd.DataFrame(data)
    if df.empty:
        log(f"[ALLIUM] Empty Allium dataset for {symbol}")
        return []

    # 🔹 Convertir fechas
    if "activity_date" in df.columns:
        df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")

    # 🔹 Normalizar símbolos (ETHEREUM → ETH, POLYGON → MATIC, etc.)
    if "chain_raw" in df.columns:
        df["symbol"] = df["chain_raw"].astype(str).str.upper().map(lambda x: CHAIN_MAP.get(x.lower(), x))
    elif "symbol" in df.columns:
        df["symbol"] = df["symbol"].astype(str).str.upper().map(lambda x: CHAIN_MAP.get(x.lower(), x))
    else:
        df["symbol"] = symbol.upper()

    # 🔹 Filtro por la chain solicitada
    symbol_norm = CHAIN_MAP.get(symbol.lower(), symbol.upper())
    df = df[df["symbol"] == symbol_norm]
    if df.empty:
        log(f"[ALLIUM] No data rows found for {symbol_norm} in Allium multi-chain dataset")
        return []

    # 🔹 Convertir campos numéricos
    numeric_cols = [
        "token_price_at_date", "token_price_current",
        "total_stake", "active_stake", "active_stake_usd",
        "circulating_supply_usd", "total_stake_usd_current",
        "active_stake_usd_current", "pct_total_stake_active",
        "pct_circulating_staked_est", "net_flow",
        "deposits_est", "withdrawals_est",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 🔹 Calcular % de circulante staked si falta
    if "pct_circulating_staked_est" not in df.columns or df["pct_circulating_staked_est"].isnull().all():
        if "total_stake_usd_current" in df.columns and "circulating_supply_usd" in df.columns:
            df["pct_circulating_staked_est"] = (
                100 * df["total_stake_usd_current"] / df["circulating_supply_usd"]
            ).round(3)

    # 🔹 Rellenar precios con CoinGecko si falta
    if market_data and isinstance(market_data, dict) and "price_usd" in market_data:
        if "token_price_current" in df.columns:
            df["token_price_current"] = df["token_price_current"].fillna(market_data["price_usd"])
        if "token_price_at_date" not in df.columns:
            df["token_price_at_date"] = market_data["price_usd"]

    # 🔹 Ordenar y devolver
    df = df.sort_values(["activity_date"], ascending=True)
    return df.to_dict(orient="records")


# ============================================================
# Core Logic (Robusto con Fallback)
# ============================================================

def fetch_chain_data(symbol, start_date, end_date, use_cache=True, no_insights=False):
    """
    Pipeline principal para obtener y combinar datos de:
    - Allium (staking)
    - CoinGecko (precios)
    - Arkham (flujos on-chain)
    - Whale Detector (movimientos en Binance)
    - GPT (insights)
    """
    symbol_norm = normalize_symbol(symbol)
    result = {}

    try:
        # 1️⃣ Cache previa
        if use_cache:
            cached = cache_get(symbol_norm, start_date, end_date)
            if cached:
                return cached

        # 2️⃣ Market (CoinGecko)
        try:
            market_data = fetch_coingecko_market(symbol_norm)
        except Exception as e:
            log(f"[COINGECKO] Error fetching {symbol_norm}: {e}")
            market_data = {}

        # 3️⃣ Allium + Fallback CSV
        try:
            raw = fetch_allium_staking(symbol_norm, start_date, end_date)
            staking_table = process_allium_staking(symbol_norm, raw, start_date, end_date, market_data)
        except Exception as e:
            log(f"[ALLIUM] Error processing {symbol_norm}: {e}")
            staking_table = []

        # Si no hay datos → fallback a CSV
        if not staking_table:
            backup_csv = "/Users/cauco/WhaleScope_Recovered/whalescope/data/allium_backup.csv"
            try:
                log(f"[ALLIUM-FALLBACK] Loading backup CSV for {symbol_norm}")
                df = pd.read_csv(backup_csv)

                df["symbol"] = df["symbol"].astype(str).str.upper().map(
                    lambda x: CHAIN_MAP.get(x.lower(), x)
                )

                # Volver a filtrar
                df = df[df["symbol"] == symbol_norm]    


                if "activity_date" in df.columns:
                    df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")

                df = df[
                    (df["activity_date"] >= start_date) &
                    (df["activity_date"] <= end_date)
                ]

                if not df.empty:
                    staking_table = df.to_dict(orient="records")
                    log(f"[ALLIUM-FALLBACK] ✅ Loaded {len(staking_table)} rows from CSV")
                else:
                    log(f"[ALLIUM-FALLBACK] CSV has no matching rows for {symbol_norm}")

            except Exception as e:
                log(f"[ALLIUM-FALLBACK] Error loading CSV: {e}")

        # 4️⃣ Arkham
        try:
            arkham_flows = fetch_arkham_flows(symbol_norm, start_date, end_date)

            if arkham_flows and isinstance(arkham_flows[0], dict) and arkham_flows[0].get("unsupported"):
                arkham_summary = {
                    "unsupported": True,
                    "total_inflow": 0,
                    "total_outflow": 0,
                    "netflow": 0,
                    "tx_count": 0
                }
            else:
                arkham_summary = {
                    "total_inflow": sum(f.get("inflow_usd", 0) for f in arkham_flows),
                    "total_outflow": sum(f.get("outflow_usd", 0) for f in arkham_flows),
                    "tx_count": len(arkham_flows),
                }
                arkham_summary["netflow"] = arkham_summary["total_inflow"] - arkham_summary["total_outflow"]

        except Exception as e:
            log(f"[ARKHAM] Error fetching {symbol_norm}: {e}")
            arkham_summary = {
                "unsupported": True,
                "total_inflow": 0,
                "total_outflow": 0,
                "netflow": 0,
                "tx_count": 0
            }

        # 5️⃣ Whale Detector (Binance)
        try:
            df_binance = fetch_binance_klines(f"{symbol_norm}USDT", interval="1d", days=90)
            whale_signals = detect_whale_flows(df_binance, symbol_norm)
            log(f"[WHALE-DETECTOR] {symbol_norm}: {len(whale_signals)} signals detected")
        except Exception as e:
            log(f"[WHALE-DETECTOR] Error for {symbol_norm}: {e}")
            whale_signals = []

        # 6️⃣ Stats
        import math
        prices = [
            float(r["token_price"]) for r in staking_table
            if r.get("token_price") not in (None, "", "NaN")
            and not math.isnan(float(r["token_price"]))
        ]

        if prices:
            stats = {
                "price_min": round(min(prices), 6),
                "price_max": round(max(prices), 6),
                "price_avg": round(statistics.mean(prices), 6),
                "price_volatility": round(statistics.pstdev(prices), 6) if len(prices) > 1 else 0.0,
            }
        else:
            stats = {k: None for k in ["price_min", "price_max", "price_avg", "price_volatility"]}

        # 7️⃣ Guardar en DB
        try:
            save_to_db(symbol_norm, staking_table)
            if whale_signals:
                save_whale_signals(symbol_norm, whale_signals)
        except Exception as e:
            log(f"[DB] Error saving {symbol_norm}: {e}")

        # 8️⃣ Insights GPT (opcional)
        insights = "Insights disabled (--no-insights)"
        if not no_insights:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)

                    prompt = (
                        f"Write a detailed Markdown report analyzing staking and whale flows for {symbol_norm}. "
                        f"Include sections: Staking Overview, Whale Movements, Market Context, Key Takeaways."
                    )

                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1200,
                        temperature=0.7,
                    )
                    insights = resp.choices[0].message.content.strip()

                except Exception as e:
                    insights = f"Error generating insights: {e}"

        # 9️⃣ Resultado final
        result = {
            "symbol": symbol_norm,
            "staking_table": staking_table or [],
            "market": market_data or {},
            "arkham_summary": arkham_summary or {},
            "whale_detector": whale_signals or [],
            "stats": stats,
            "insights": insights,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": ["allium", "arkham", "coingecko", "binance"],
        }

        #  🔹 Extra: whales_flows (compatibilidad con otros módulos)
        try:
            if staking_table:
                result["whales_flows"] = {
                    "dates": [r.get("activity_date") for r in staking_table],
                    "inflows": [float(r.get("deposits_est", 0)) for r in staking_table],
                    "outflows": [float(r.get("withdrawals_est", 0)) for r in staking_table],
                    "net": [float(r.get("net_flow", 0)) for r in staking_table]
                }
        except Exception as e:
            log(f"[CACHE] Skipping whales_flows for {symbol_norm}: {e}")

        # 10️⃣ Guardar en Cache
        if use_cache:
            cache_set(symbol_norm, start_date, end_date, result)

    except Exception as e:
        log(f"[FATAL] {symbol_norm}: {e}")
        result = {
            "symbol": symbol_norm,
            "error": str(e),
            "staking_table": [],
            "market": {},
            "arkham_summary": {},
            "stats": {},
            "insights": f"Error: {e}",
        }

    return result


def fetch_staking_data(symbol, start_date, end_date):
    """
    Devuelve flujos on-chain (staking o whales_flows) del símbolo especificado.
    Lee desde los archivos de cache generados por staking_analysis.py o marketbrain.
    Si no encuentra data, devuelve None sin romper el flujo.
    """
    import os, json
    from datetime import datetime

    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")

    if not os.path.exists(cache_dir):
        print(f"[OnChain] Cache directory not found: {cache_dir}")
        return None

    # Buscar archivo de cache más reciente que contenga el símbolo
    files = [
        f for f in os.listdir(cache_dir)
        if symbol.upper() in f and f.endswith(".json")
    ]
    if not files:
        print(f"[OnChain] No cache file for {symbol}")
        return None

    files.sort(key=lambda f: os.path.getmtime(os.path.join(cache_dir, f)), reverse=True)
    path = os.path.join(cache_dir, files[0])

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[OnChain] Error reading cache file for {symbol}: {e}")
        return None

    whales_flows = (
        data.get("whales_flows")
        or data.get("staking_flows")
        or data.get("network_flows")
    )

    if not whales_flows:
        print(f"[OnChain] No whales_flows in cache for {symbol}")
        return None

    # 🔹 Filtrar fechas dentro del rango solicitado
    try:
        dates = whales_flows.get("dates", [])
        inflows = whales_flows.get("inflows", [])
        outflows = whales_flows.get("outflows", [])
        net = whales_flows.get("net", [])

        if dates:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            filtered = [
                (d, i, o, n)
                for d, i, o, n in zip(dates, inflows, outflows, net)
                if start_dt <= datetime.strptime(d[:10], "%Y-%m-%d") <= end_dt
            ]

            if filtered:
                dates, inflows, outflows, net = zip(*filtered)
                whales_flows = {
                    "dates": list(dates),
                    "inflows": list(inflows),
                    "outflows": list(outflows),
                    "net": list(net)
                }
                print(f"[OnChain] {symbol}: {len(dates)} días con data on-chain")
    except Exception as e:
        print(f"[OnChain] Error filtering dates for {symbol}: {e}")

    return {"whales_flows": whales_flows}
   


# ============================================================
# Main (con soporte --format y fallback seguro)
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="MarketBrain Allium-based staking analysis")
    parser.add_argument("--chains", nargs="+", required=True, help="Chains to analyze (ETH, SOL, etc.)")
    parser.add_argument("--from", dest="start_date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end_date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-cache", action="store_true", help="Disable local cache")
    parser.add_argument("--no-insights", action="store_true", help="Skip GPT insights")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (json or csv)")
    args = parser.parse_args()

    load_dotenv()

    # ============================================================
    # 🔹 Procesar cada chain individualmente con tolerancia a errores
    # ============================================================
    results = {}
    for sym in args.chains:
        try:
            results[sym] = fetch_chain_data(
                sym,
                args.start_date,
                args.end_date,
                use_cache=not args.no_cache,
                no_insights=args.no_insights
            )
        except Exception as e:
            log(f"[ERROR] Failed to process {sym}: {e}")
            # 🔸 Fallback mínimo (para no romper el JSON final)
            results[sym] = {
                "symbol": sym,
                "error": str(e),
                "results": [],
                "staking_table": [],
                "status": "error"
            }

    # ============================================================
    # ✅ Construcción del resultado final
    # ============================================================
    output = {
        "type": "marketbrain",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "source": "MarketBrain-Ultimate",
    }

    # ============================================================
    # 🔸 Salida según formato solicitado
    # ============================================================
    if args.format == "json":
        try:
            import os, io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='', write_through=True)
            os.environ["PYTHONUNBUFFERED"] = "1"

            safe_output = json.dumps(
                clean_nans(output),
                ensure_ascii=False,
                separators=(",", ":"),
                default=str
            ).strip()

            os.write(sys.stdout.fileno(), safe_output.encode("utf-8"))
            sys.stdout.flush()

        except Exception as e:
            log(f"[ERROR] JSON serialization failed: {e}")
            err_json = json.dumps({"error": f"Serialization failed: {e}"})
            os.write(sys.stdout.fileno(), err_json.encode("utf-8"))
            sys.stdout.flush()

    elif args.format == "csv":
        import csv

        def fmt_usd(x):
            if x in (None, "", "NaN"):
                return ""
            x = float(x)
            if abs(x) >= 1_000_000_000:
                return f"{x/1_000_000_000:.2f}B"
            if abs(x) >= 1_000_000:
                return f"{x/1_000_000:.2f}M"
            return f"{x:,.0f}"

        def fmt_pct(x):
            if x in (None, "", "NaN"):
                return ""
            return f"{float(x):.2f}%"

        writer = csv.writer(sys.stdout)
        writer.writerow([
            "Date", "Symbol",
            "Active Stake (USD)", "Total Stake (USD)",
            "% Active Stake", "% Circulating Staked",
            "Net Flow (USD)", "Deposits (USD)", "Withdrawals (USD)",
            "Token Price (USD)"
        ])

        for sym, result in results.items():
            for row in result.get("staking_table", []):
                writer.writerow([
                    str(row.get("activity_date", ""))[:10],
                    row.get("symbol"),
                    fmt_usd(row.get("active_stake_usd_current")),
                    fmt_usd(row.get("total_stake_usd_current")),
                    fmt_pct(row.get("pct_total_stake_active")),
                    fmt_pct(row.get("pct_circulating_staked_est")),
                    fmt_usd(row.get("net_flow")),
                    fmt_usd(row.get("deposits_est")),
                    fmt_usd(row.get("withdrawals_est")),
                    f"{float(row.get('token_price_at_date')):.2f}" if row.get("token_price_at_date") else ""
                ])


# ============================================================
# Punto de entrada
# ============================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"❌ Fatal error in main(): {e}")
        err_json = json.dumps({"error": str(e)})
        sys.stdout.write(err_json)
        sys.stdout.flush()
    # ✅ No usar sys.exit()


# =========================================================
# ⏭️ ETH Merge deshabilitado temporalmente (path mismatch)
# =========================================================
log("⏭️ Skipping ETH merge (disabled to prevent DB lock issues)")