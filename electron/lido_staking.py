# lido_staking.py

import requests
import sqlite3
from datetime import datetime, timedelta
import os
import json
import time
import sys
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from appdirs import user_log_dir  # Import appdirs for platform-specific log directory
import logging  # Import logging module

# Configure logging to write to a platform-appropriate directory
# Use appdirs to determine a writable log directory (e.g., ~/Library/Logs/WhaleScope on macOS)
log_dir = user_log_dir("WhaleScope", "Cauco")  # App name: WhaleScope, author: Cauco
os.makedirs(log_dir, exist_ok=True)  # Create the log directory if it doesn't exist
log_file = os.path.join(log_dir, "lido_staking.log")  # Define log file path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # Write to platform-specific log file
        logging.StreamHandler(sys.stderr)  # Keep stderr for compatibility with existing prints
    ]
)
logger = logging.getLogger(__name__)

# API Keys
CMC_API_KEY = os.getenv("CMC_API_KEY", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
CMC_BASE_URL = "https://pro-api.coinmarketcap.com"
ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"

# CoinMarketCap IDs
IDS = {
    "STETH": {"cmc": 8085},
    "WSTETH": {"cmc": 12409},
    "ETH": {"cmc": 1027}
}

# Lido Smart Contract
LIDO_CONTRACT_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"

# Current date
current_date = datetime.now()
current_date_str = current_date.strftime('%Y-%m-%d')

# SQLite database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "whalescope.db")  # Use relative path to whalescope.db
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS liquid_staking_pools
                  (pool_name TEXT, total_eth_deposited REAL, eth_staked REAL, eth_unstaked REAL,
                   staking_rewards REAL, timestamp TEXT, week_end TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS eth_staking_queues
                  (queue_type TEXT, eth_amount REAL, avg_wait_time REAL, timestamp TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS eth_staking_ratio
                  (date TEXT, staking_ratio REAL, avg_rewards REAL, timestamp TEXT)''')
conn.commit()

# Configure request retries
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

def fetch_etherscan_data(action, symbol=None, retries=3):
    logger.info(f"Starting fetch_etherscan_data for {action}, symbol: {symbol}")
    params = {
        "module": "stats" if action == "ethsupply" else "account",
        "action": "balance" if action == "ethbalance" else action,
        "apikey": ETHERSCAN_API_KEY
    }
    if action == "ethbalance" and symbol == "LIDO":
        params["address"] = LIDO_CONTRACT_ADDRESS
    for attempt in range(retries):
        try:
            time.sleep(0.2)
            response = session.get(ETHERSCAN_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data["status"] != "1":
                raise ValueError(f"Etherscan error: {data.get('message', 'Unknown error')}")
            result = int(data["result"]) / 10**18
            logger.info(f"Etherscan {action} for {symbol or 'ETH'}: {result} ETH")
            return result
        except Exception as e:
            logger.error(f"Attempt {attempt+1}/{retries} failed for Etherscan {action}: {e}")
            if attempt == retries - 1:
                logger.error(f"Failed to fetch Etherscan data for {action} after {retries} attempts.")
                return None
            time.sleep(0.5 * (attempt + 1))

def fetch_cmc_data(cmc_id, symbol):
    logger.info(f"Fetching data for {symbol} (ID: {cmc_id}) from CoinMarketCap")
    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accept": "application/json"
    }
    params = {
        "id": cmc_id,
        "convert": "USD"
    }
    url = f"{CMC_BASE_URL}/v1/cryptocurrency/quotes/latest"
    try:
        response = session.get(url, headers=headers, params=params)
        if response.status_code == 400:
            raise ValueError(f"HTTP 400: Invalid request for {symbol} (ID: {cmc_id})")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"CoinMarketCap response for {symbol}: {json.dumps(data, indent=2)}")
        if "data" not in data or str(cmc_id) not in data["data"]:
            raise ValueError(f"Invalid CoinMarketCap response for {symbol}: missing data")
        adapted_data = {
            "data": {
                str(cmc_id): {
                    "circulating_supply": data["data"][str(cmc_id)].get("circulating_supply", 0),
                    "quote": {
                        "USD": {
                            "price": data["data"][str(cmc_id)]["quote"]["USD"].get("price", 0)
                        }
                    }
                }
            }
        }
        if adapted_data["data"][str(cmc_id)]["circulating_supply"] <= 0:
            raise ValueError(f"Invalid CoinMarketCap circulating supply for {symbol}")
        if adapted_data["data"][str(cmc_id)]["quote"]["USD"]["price"] <= 0:
            raise ValueError(f"Invalid CoinMarketCap price for {symbol}")
        return adapted_data
    except Exception as e:
        logger.error(f"Error fetching CoinMarketCap data for {symbol} (ID: {cmc_id}): {e}")
        return None

def fetch_token_data(symbol):
    logger.info(f"Fetching token data for {symbol}")
    cmc_id = IDS[symbol]["cmc"]
    data = fetch_cmc_data(cmc_id, symbol)
    if data and symbol == "ETH":
        eth_supply = fetch_etherscan_data("ethsupply")
        if eth_supply and eth_supply > 0:
            data["data"][str(cmc_id)]["circulating_supply"] = eth_supply
            logger.info(f"Using Etherscan supply for ETH: {eth_supply}")
    return data

def fetch_lido_data(week_end=None):
    logger.info(f"Fetching Lido Data for week ending {week_end or 'current'}")
    try:
        steth_data = fetch_token_data("STETH")
        logger.debug("STETH data fetched: %s", steth_data is not None)
        wsteth_data = fetch_token_data("WSTETH")
        logger.debug("WSTETH data fetched: %s", wsteth_data is not None)
        eth_data = fetch_token_data("ETH")
        logger.debug("ETH data fetched: %s", eth_data is not None)

        if not (steth_data and wsteth_data and eth_data):
            logger.error("Failed to fetch data for STETH, WSTETH, or ETH.")
            return None

        steth_info = steth_data["data"][str(IDS["STETH"]["cmc"])]
        wsteth_info = wsteth_data["data"][str(IDS["WSTETH"]["cmc"])]
        eth_info = eth_data["data"][str(IDS["ETH"]["cmc"])]

        steth_supply = steth_info["circulating_supply"]
        wsteth_supply = wsteth_info["circulating_supply"]

        steth_price_usd = steth_info["quote"]["USD"]["price"]
        wsteth_price_usd = wsteth_info["quote"]["USD"]["price"]
        eth_price_usd = eth_info["quote"]["USD"]["price"]

        if steth_price_usd <= 0:
            logger.error(f"Invalid STETH price ({steth_price_usd}).")
            return None
        wsteth_to_eth_ratio = wsteth_price_usd / steth_price_usd
        eth_staked = steth_supply + (wsteth_supply * wsteth_to_eth_ratio)

        eth_unstaked = fetch_etherscan_data("ethbalance", "LIDO")
        if not eth_unstaked or eth_unstaked <= 10000:
            logger.warning(f"Invalid or low eth_unstaked: {eth_unstaked}. Using default.")
            eth_unstaked = 87479

        total_eth_deposited = eth_staked + eth_unstaked

        lido_api_url = "https://eth-api.lido.fi/v1/protocol/steth/apr/last"
        try:
            response = session.get(lido_api_url)
            response.raise_for_status()
            lido_response = response.json()
            logger.debug(f"Lido API raw response: {json.dumps(lido_response, indent=2)}")
            apr = lido_response.get("data", {}).get("apr", 3.5) / 100
            logger.info(f"APR fetched from Lido: {apr*100}%")
        except Exception as e:
            logger.warning(f"Failed to fetch APR from Lido API: {e}. Using default.")
            apr = 3.5 / 100

        staking_rewards = eth_staked * apr

        data = {
            "pool_name": "Lido",
            "total_eth_deposited": float(total_eth_deposited),
            "eth_staked": float(eth_staked),
            "eth_unstaked": float(eth_unstaked),
            "staking_rewards": float(staking_rewards),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "week_end": week_end or current_date_str
        }
        logger.info(f"Lido data fetched: {json.dumps(data, indent=2)}")
        return data
    except Exception as e:
        logger.error(f"Error fetching Lido data: {e}")
        return None

def fetch_staking_queues():
    logger.info("Fetching Stake/Unstake Queue Data")
    try:
        beaconchain_url = "https://beaconcha.in/api/v1/validators/queue"
        response = session.get(beaconchain_url)
        response.raise_for_status()
        queue_data = response.json()

        validators_to_enter = queue_data["data"]["beaconchain_entering"]
        validators_to_exit = queue_data["data"]["beaconchain_exiting"]
        eth_in_stake_queue = validators_to_enter * 32
        eth_in_unstake_queue = validators_to_exit * 32

        avg_wait_time_stake = 5.58 * 24 * 60 * 60
        avg_wait_time_unstake = 5.58 * 24 * 60 * 60

        queues = [
            {"queue_type": "stake", "eth_amount": float(eth_in_stake_queue), "avg_wait_time": float(avg_wait_time_stake)},
            {"queue_type": "unstake", "eth_amount": float(eth_in_unstake_queue), "avg_wait_time": float(avg_wait_time_unstake)}
        ]
        logger.info(f"Stake/Unstake queues: {json.dumps(queues, indent=2)}")
        return queues
    except Exception as e:
        logger.error(f"Error fetching queue data: {e}")
        return []

def fetch_staking_ratio():
    logger.info("Fetching Staking Ratio")
    try:
        eth_data = fetch_token_data("ETH")
        if not eth_data:
            logger.error("Failed to fetch ETH data.")
            return None

        eth_info = eth_data["data"][str(IDS["ETH"]["cmc"])]
        total_supply = eth_info["circulating_supply"]
        if total_supply <= 0:
            logger.error(f"Invalid ETH circulating supply ({total_supply}).")
            return None

        steth_data = fetch_token_data("STETH")
        wsteth_data = fetch_token_data("WSTETH")
        if not (steth_data and wsteth_data):
            logger.error("Failed to fetch stETH/wstETH data.")
            return None

        steth_info = steth_data["data"][str(IDS["STETH"]["cmc"])]
        wsteth_info = wsteth_data["data"][str(IDS["WSTETH"]["cmc"])]
        steth_supply = steth_info["circulating_supply"]
        wsteth_supply = wsteth_info["circulating_supply"]
        steth_price_usd = steth_info["quote"]["USD"]["price"]
        wsteth_price_usd = wsteth_info["quote"]["USD"]["price"]

        if steth_price_usd <= 0:
            logger.error(f"Invalid STETH price ({steth_price_usd}).")
            return None
        wsteth_to_eth_ratio = wsteth_price_usd / steth_price_usd
        eth_staked_total = steth_supply + (wsteth_supply * wsteth_to_eth_ratio)

        staking_ratio = eth_staked_total / total_supply

        lido_api_url = "https://eth-api.lido.fi/v1/protocol/steth/apr/last"
        try:
            response = session.get(lido_api_url)
            response.raise_for_status()
            lido_response = response.json()
            logger.debug(f"Lido API raw response: {json.dumps(lido_response, indent=2)}")
            avg_rewards = lido_response.get("data", {}).get("apr", 3.5) / 100
            logger.info(f"APR for staking ratio: {avg_rewards*100}%")
        except Exception as e:
            logger.warning(f"Failed to fetch APR from Lido API: {e}. Using default.")
            avg_rewards = 3.5 / 100

        data = {
            "date": current_date_str,
            "staking_ratio": float(staking_ratio),
            "avg_rewards": float(avg_rewards),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        logger.info(f"Staking ratio: {json.dumps(data, indent=2)}")
        return data
    except Exception as e:
        logger.error(f"Error fetching staking ratio: {e}")
        return None

def save_historical_data(start_date, end_date):
    logger.info(f"Populating historical Lido data from {start_date} to {end_date}")
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if start > end:
            raise ValueError("Start date must be before or equal to end date")
        delta = end - start
        historical_data = []
        for i in range(0, delta.days + 1, 7):  # Weekly data
            week_end = (start + timedelta(days=i)).strftime('%Y-%m-%d')
            data = fetch_lido_data(week_end)
            if data:
                cursor.execute("""
                    INSERT OR REPLACE INTO liquid_staking_pools
                    (pool_name, total_eth_deposited, eth_staked, eth_unstaked, staking_rewards, timestamp, week_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data["pool_name"], data["total_eth_deposited"], data["eth_staked"],
                      data["eth_unstaked"], data["staking_rewards"], data["timestamp"], week_end))
                historical_data.append({
                    "week_end": week_end,
                    "total_eth_deposited": data["total_eth_deposited"],
                    "eth_staked": data["eth_staked"],
                    "eth_unstaked": data["eth_unstaked"],
                    "staking_rewards": data["staking_rewards"]
                })
        conn.commit()
        return historical_data
    except Exception as e:
        logger.error(f"Error in save_historical_data: {e}")
        return []

def save_data(start_date=None, end_date=None):
    logger.info("Starting save_data")
    historical_data = []
    lido_data = None
    queues = []
    ratio_data = None

    try:
        if start_date and end_date:
            historical_data = save_historical_data(start_date, end_date)
        else:
            lido_data = fetch_lido_data()
            if lido_data:
                logger.info("Saving liquid_staking_pools")
                cursor.execute("""
                    INSERT OR REPLACE INTO liquid_staking_pools
                    (pool_name, total_eth_deposited, eth_staked, eth_unstaked, staking_rewards, timestamp, week_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (lido_data["pool_name"], lido_data["total_eth_deposited"], lido_data["eth_staked"],
                      lido_data["eth_unstaked"], lido_data["staking_rewards"], lido_data["timestamp"], current_date_str))
                conn.commit()

        queues = fetch_staking_queues()
        if queues:
            logger.info("Saving eth_staking_queues")
            for queue in queues:
                cursor.execute("""
                    INSERT OR REPLACE INTO eth_staking_queues
                    (queue_type, eth_amount, avg_wait_time, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (queue["queue_type"], queue["eth_amount"], queue["avg_wait_time"],
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()

        ratio_data = fetch_staking_ratio()
        if ratio_data:
            logger.info("Saving eth_staking_ratio")
            cursor.execute("""
                INSERT OR REPLACE INTO eth_staking_ratio
                (date, staking_ratio, avg_rewards, timestamp)
                VALUES (?, ?, ?, ?)
                """, (ratio_data["date"], ratio_data["staking_ratio"], ratio_data["avg_rewards"],
                      ratio_data["timestamp"]))
            conn.commit()

        # Write output to a writable directory
        output_dir = user_log_dir("WhaleScope", "Cauco")  # Use same directory as logs
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "lido_output.json")

        output_data = {
            "markets": {
                "stETH": {
                    "total_eth_deposited": lido_data["total_eth_deposited"] if lido_data else 0,
                    "eth_staked": lido_data["eth_staked"] if lido_data else 0,
                    "eth_unstaked": lido_data["eth_unstaked"] if lido_data else 0,
                    "staking_rewards": lido_data["staking_rewards"] if lido_data else 0,
                    "last_updated": lido_data["timestamp"] if lido_data else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            },
            "yields": {
                "avg_rewards": ratio_data["avg_rewards"] * 100 if ratio_data else 3.5
            },
            "analytics": {
                "staking_ratio": ratio_data["staking_ratio"] if ratio_data else 0,
                "queues": queues if queues else []
            },
            "charts": historical_data
        }

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=4)
        logger.info(f"Data saved to {output_file}")
        return output_data

    except Exception as e:
        logger.error(f"Error in save_data: {e}")
        return {
            "markets": {"stETH": {"total_eth_deposited": 0, "eth_staked": 0, "eth_unstaked": 0, "staking_rewards": 0, "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}},
            "yields": {"avg_rewards": 3.5},
            "analytics": {"staking_ratio": 0, "queues": []},
            "charts": [],
            "error": str(e)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lido staking data fetcher")
    parser.add_argument('--start-date', type=str, help="Start date for historical data (YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, help="End date for historical data (YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        output_data = save_data(start_date=args.start_date, end_date=args.end_date)
        print(json.dumps(output_data, indent=4))
    except Exception as e:
        logger.error(f"Script failed: {e}")
        print(json.dumps({"error": str(e)}, indent=4), file=sys.stdout)
    finally:
        logger.info("Closing database connection")
        conn.close()
    sys.stdout.flush()