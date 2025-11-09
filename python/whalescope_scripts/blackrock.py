import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import requests
from appdirs import user_log_dir
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress matplotlib font debugging logs
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Configure logging
log_dir = user_log_dir("WhaleScope", "Cauco")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "blackrock.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Constants
DB_PATH = os.path.join(os.path.dirname(__file__), 'whalescope.db')
ARKHAM_API_KEY = os.getenv("ARKHAM_API_KEY")
PLOT_DIR = os.path.join(user_log_dir("WhaleScope", "Cauco"), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# FED news events
FED_EVENTS = [
    {"date": "2024-09-18", "event": "FED expected to cut rates by 25-50 bps", "source": "web:1, web:8, web:9"},
    {"date": "2024-12-19", "event": "FED cuts rates by 25 bps, signals pause in January 2025", "source": "web:2"},
    {"date": "2025-07-25", "event": "BlackRock's Rogal and Wolfe's Roth discuss FED rate cut expectations", "source": "web:0"},
]

# Fallback addresses (add known BlackRock addresses if available)
FALLBACK_ADDRESSES = []  # Replace with actual addresses, e.g., ["0x_known_address_1", "0x_known_address_2"]

def create_session():
    """Create a requests session with retry configuration."""
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": "WhaleScope/1.0 (BlackRockScript)"})
    return session

def save_intermediate_output(output_dir, data, filename):
    """Save intermediate JSON output."""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, filename)
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Intermediate data saved to {output_file}")

def migrate_arkham_transactions(cursor):
    """Migrate arkham_transactions table to include 'token' column if missing."""
    logger.info("Migrating arkham_transactions table to include token column")
    cursor.execute("ALTER TABLE arkham_transactions RENAME TO arkham_transactions_old")
    cursor.execute('''CREATE TABLE arkham_transactions (
        entity_id TEXT, date TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, 
        amount_usd REAL NOT NULL, token TEXT NOT NULL,
        PRIMARY KEY (entity_id, date, type, token)
    )''')
    cursor.execute('''
        INSERT INTO arkham_transactions (entity_id, date, type, amount, amount_usd, token)
        SELECT entity_id, date, type, amount, amount_usd, 'UNKNOWN' 
        FROM arkham_transactions_old
    ''')
    cursor.execute("DROP TABLE arkham_transactions_old")

def init_db():
    """Initialize database tables and indexes."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(arkham_transactions)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'token' not in columns:
            migrate_arkham_transactions(cursor)
        cursor.execute('''CREATE TABLE IF NOT EXISTS arkham_wallets (
            entity_id TEXT, token TEXT NOT NULL, balance REAL NOT NULL, balance_usd REAL NOT NULL, 
            timestamp TEXT NOT NULL,
            PRIMARY KEY (entity_id, token, timestamp)
        )''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_wallets_timestamp 
                         ON arkham_wallets (entity_id, token, timestamp)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_transactions_token 
                         ON arkham_transactions (entity_id, token, date)''')
        conn.commit()
        logger.info("Database tables and indexes initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

def check_api_key(api_key):
    """Validate the Arkham API key."""
    endpoint = "https://api.arkhamintelligence.com/health"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    with create_session() as session:
        try:
            logger.info(f"Checking API key validity at {endpoint}")
            response = session.get(endpoint, headers=headers, timeout=20)
            response.raise_for_status()
            logger.info(f"API key is valid. Response: {response.text}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to validate API key: {e} | Status: {getattr(e.response, 'status_code', 'N/A')}")
            return False

def fetch_blackrock_entity(api_key):
    """Fetch BlackRock entity data from Arkham API."""
    base_url = "https://api.arkhamintelligence.com"
    endpoint = f"{base_url}/intelligence/entity/blackrock"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    with create_session() as session:
        try:
            logger.info(f"Fetching BlackRock entity data from {endpoint}")
            response = session.get(endpoint, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            entity_id = data.get('id')
            if not entity_id:
                logger.error(f"No id found in BlackRock entity data: {data}")
                return None
            logger.info(f"Successfully fetched BlackRock entity data: {entity_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch BlackRock entity data: {e} | Status: {getattr(e.response, 'status_code', 'N/A')}")
            return None

def fetch_blackrock_addresses(api_key, entity_id):
    """Fetch addresses associated with BlackRock entity."""
    base_url = "https://api.arkhamintelligence.com"
    endpoint = f"{base_url}/intelligence/entity/{entity_id}/addresses"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    with create_session() as session:
        try:
            logger.info(f"Fetching addresses for entity {entity_id}")
            response = session.get(endpoint, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            addresses = data.get('addresses', [])
            logger.info(f"Fetched {len(addresses)} addresses: {addresses[:5]}")
            return addresses
        except requests.RequestException as e:
            logger.error(f"Failed to fetch addresses: {e} | Status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.warning("Using fallback addresses due to API failure")
            return FALLBACK_ADDRESSES

def fetch_arkham_balances(api_key, entity_id):
    """Fetch balance data for a given entity from Arkham API."""
    base_url = "https://api.arkhamintelligence.com"
    url = f"{base_url}/balances/entity/{entity_id}"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    with create_session() as session:
        try:
            logger.info(f"Fetching balances for entity {entity_id}")
            response = session.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            balances = []
            balances_dict = data.get('balances', {})
            for chain in balances_dict:
                chain_balances = balances_dict.get(chain, [])
                if isinstance(chain_balances, list):
                    balances.extend([balance for balance in chain_balances if 'symbol' in balance and 'balance' in balance and 'usd' in balance])
            logger.info(f"Fetched {len(balances)} balances from Arkham")
            return balances
        except requests.RequestException as e:
            logger.error(f"Failed to fetch balances: {e} | Status: {getattr(e.response, 'status_code', 'N/A')}")
            return []

def fetch_arkham_transactions(api_key, entity_id, start_date, end_date, symbol=None):
    """Fetch transaction history for a given entity from Arkham API."""
    base_url = "https://api.arkhamintelligence.com"
    url = f"{base_url}/history/entity/{entity_id}"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    params = {"startDate": start_date, "endDate": end_date, "limit": 100}
    if symbol:
        params["tokenSymbol"] = symbol.upper()
    transactions = []
    with create_session() as session:
        try:
            logger.info(f"Fetching transactions for entity {entity_id} from {start_date} to {end_date}{f' for {symbol}' if symbol else ''}")
            while True:
                response = session.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                data = response.json()
                transactions.extend(data.get('transfers', []))
                if not (next_page := data.get('nextPage')):
                    break
                params['page'] = next_page
            logger.info(f"Fetched {len(transactions)} transactions")
            return transactions
        except requests.RequestException as e:
            logger.error(f"Failed to fetch transactions: {e} | Status: {getattr(e.response, 'status_code', 'N/A')}")
            return transactions
        finally:
            session.close()

def fetch_address_transactions(api_key, address, start_date, end_date, symbol=None):
    """Fetch transaction history for a specific address."""
    base_url = "https://api.arkhamintelligence.com"
    url = f"{base_url}/history/address/{address}"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    params = {"startDate": start_date, "endDate": end_date, "limit": 100}
    if symbol:
        params["tokenSymbol"] = symbol.upper()
    transactions = []
    with create_session() as session:
        try:
            logger.info(f"Fetching transactions for address {address} from {start_date} to {end_date}")
            while True:
                response = session.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                data = response.json()
                transactions.extend(data.get('transfers', []))
                if not (next_page := data.get('nextPage')):
                    break
                params['page'] = next_page
            logger.info(f"Fetched {len(transactions)} transactions for address {address}")
            return transactions
        except requests.RequestException as e:
            logger.error(f"Failed to fetch transactions for address {address}: {e}")
            return transactions
        finally:
            session.close()

def process_exchange_usage(transactions, entity_id):
    """Process exchange usage (deposits and withdrawals) from transactions."""
    try:
        logger.info(f"Processing exchange usage for entity {entity_id}")
        deposits = {"total": 0, "summary": []}
        withdrawals = {"total": 0, "summary": []}
        for transfer in transactions:
            usd_value = float(transfer.get('usdValue', 0))
            from_address = transfer.get('fromAddress', '')
            to_address = transfer.get('toAddress', '')
            if isinstance(from_address, dict):
                from_address = from_address.get('address', '')
            if isinstance(to_address, dict):
                to_address = to_address.get('address', '')
            if 'exchange' in from_address.lower():
                withdrawals["total"] += usd_value
                withdrawals["summary"].append(transfer)
            elif 'exchange' in to_address.lower():
                deposits["total"] += usd_value
                deposits["summary"].append(transfer)
        logger.info(f"Exchange usage: Deposits ${deposits['total']:,.2f}, Withdrawals ${withdrawals['total']:,.2f}")
        return {"deposits": deposits, "withdrawals": withdrawals}
    except Exception as e:
        logger.error(f"Failed to process exchange usage: {e}")
        return {"deposits": {"total": 0, "summary": []}, "withdrawals": {"total": 0, "summary": []}}

def derive_prices_from_balances(balances, start_date, end_date):
    """Derive historical prices from Arkham balances."""
    prices = {'BTC': {}, 'ETH': {}, 'USDC': {}}
    try:
        logger.info("Deriving prices for BTC, ETH, and USDC from Arkham balances")
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        delta = end - start
        for i in range(0, delta.days + 1, 7):
            date = (start + timedelta(days=i)).strftime('%Y-%m-%d')
            for balance in balances:
                token = balance.get('symbol', '').upper()
                if token in ['BTC', 'ETH', 'USDC']:
                    balance_amount = float(balance.get('balance', 0))
                    balance_usd = float(balance.get('usd', 0))
                    if balance_amount > 0:
                        prices[token][date] = round(balance_usd / balance_amount, 2)
                    else:
                        prices[token][date] = 1.0 if token == 'USDC' else 0.0
        logger.info(f"Derived {len(prices['BTC'])} prices for BTC, {len(prices['ETH'])} for ETH, {len(prices['USDC'])} for USDC")
        return prices
    except Exception as e:
        logger.error(f"Failed to derive prices: {e}")
        return prices

def ensure_historical_wallet_data(entity_id, start_date, end_date, balances, historical_prices):
    """Populate historical wallet data with price-adjusted USD values."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        cursor.execute('''
            DELETE FROM arkham_wallets 
            WHERE entity_id = ? 
            AND timestamp BETWEEN ? AND ?
        ''', (entity_id, start.strftime('%Y-%m-%d 00:00:00'), end.strftime('%Y-%m-%d 23:59:59')))
        conn.commit()
        delta = end - start
        inserted = 0
        aggregated_balances = {}
        for balance in balances:
            token = balance['symbol'].upper()
            balance_amount = float(balance.get('balance', 0))
            balance_usd = float(balance.get('usd', 0))
            if token in aggregated_balances:
                aggregated_balances[token]['balance'] += balance_amount
                aggregated_balances[token]['usd'] += balance_usd
            else:
                aggregated_balances[token] = {'symbol': token, 'balance': balance_amount, 'usd': balance_usd}
        for token, agg_balance in aggregated_balances.items():
            for i in range(0, delta.days + 1, 7):
                timestamp = (start + timedelta(days=i)).strftime('%Y-%m-%d 12:00:00')
                date = (start + timedelta(days=i)).strftime('%Y-%m-%d')
                price = historical_prices.get(token, {}).get(date, 0.0)
                adjusted_usd = agg_balance['balance'] * price if price else agg_balance['usd']
                cursor.execute('''
                    INSERT OR REPLACE INTO arkham_wallets (entity_id, token, balance, balance_usd, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (entity_id, token, agg_balance['balance'], adjusted_usd, timestamp))
                inserted += 1
        conn.commit()
        logger.info(f"Populated {inserted} historical wallet entries")
        return list(aggregated_balances.values())
    except Exception as e:
        logger.error(f"Failed to ensure historical wallet data: {e}")
        return balances
    finally:
        if 'conn' in locals():
            conn.close()

def fetch_historical_balances(entity_id, start_date, end_date):
    """Fetch historical balances for BTC, ETH, and USDC from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
        cursor.execute('''
            SELECT token, balance, balance_usd, timestamp,
                   strftime('%Y-%W', timestamp) as week
            FROM (
                SELECT token, balance, balance_usd, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY token, strftime('%Y-%W', timestamp) 
                                         ORDER BY timestamp DESC) as rn
                FROM arkham_wallets 
                WHERE entity_id = ? AND token IN ('BTC', 'ETH', 'USDC')
                AND timestamp BETWEEN ? AND ?
            )
            WHERE rn = 1
            ORDER BY timestamp
        ''', (entity_id, start_datetime, end_datetime))
        balances = {'BTC': [], 'ETH': [], 'USDC': []}
        for row in cursor.fetchall():
            token, balance, balance_usd, timestamp, week = row
            year, week_num = map(int, week.split('-'))
            week_end = datetime.strptime(f'{year}-W{week_num}-6', '%Y-W%W-%w').strftime('%Y-%m-%d')
            balances[token].append({
                'week_end': week_end,
                'balance': float(balance),
                'balance_usd': float(balance_usd)
            })
        logger.info(f"Fetched {len(balances['BTC'])} BTC, {len(balances['ETH'])} ETH, {len(balances['USDC'])} USDC balances")
        return balances
    except Exception as e:
        logger.error(f"Failed to fetch historical balances: {e}")
        return {'BTC': [], 'ETH': [], 'USDC': []}
    finally:
        if 'conn' in locals():
            conn.close()

def fetch_historical_total_balance(entity_id, start_date, end_date):
    """Fetch historical total balance across all tokens from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
        cursor.execute('''
            SELECT strftime('%Y-%W', timestamp) as week,
                   SUM(balance_usd) as total_balance_usd
            FROM arkham_wallets
            WHERE entity_id = ?
            AND timestamp BETWEEN ? AND ?
            GROUP BY strftime('%Y-%W', timestamp)
            ORDER BY timestamp
        ''', (entity_id, start_datetime, end_datetime))
        total_balances = []
        for row in cursor.fetchall():
            week, total_balance_usd = row
            year, week_num = map(int, week.split('-'))
            week_end = datetime.strptime(f'{year}-W{week_num}-6', '%Y-W%W-%w').strftime('%Y-%m-%d')
            total_balances.append({
                'week_end': week_end,
                'total_balance_usd': float(total_balance_usd)
            })
        logger.info(f"Fetched {len(total_balances)} weekly total balances")
        return total_balances
    except Exception as e:
        logger.error(f"Failed to fetch historical total balance: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def process_transactions(transactions, historical_prices, symbol=None):
    """Process and store transactions in the database."""
    result = {}
    inserted = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for tx in transactions:
            token = tx.get('tokenSymbol', '').upper()
            if symbol and token != symbol.upper():
                continue
            date = tx.get('blockTimestamp', '').split('T')[0]
            if not date:
                continue
            to_address = tx.get('toAddress', '')
            if isinstance(to_address, dict):
                to_address = to_address.get('address', '')
            tx_type = 'buy' if 'blackrock' in to_address.lower() else 'sell'
            amount = float(tx.get('unitValue', 0))
            amount_usd = float(tx.get('usdValue', 0))
            if amount < 0.1:
                continue
            if token not in result:
                result[token] = {}
            if date not in result[token]:
                result[token][date] = {'buys': 0.0, 'sells': 0.0, 'buys_usd': 0.0, 'sells_usd': 0.0}
            price = historical_prices.get(token, {}).get(date, 0.0)
            if tx_type == 'buy':
                result[token][date]['buys'] += amount
                result[token][date]['buys_usd'] += amount * price if price else amount_usd
            else:
                result[token][date]['sells'] += amount
                result[token][date]['sells_usd'] += amount * price if price else amount_usd
            cursor.execute('''
                INSERT OR REPLACE INTO arkham_transactions (entity_id, date, type, amount, amount_usd, token)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('blackrock', date, tx_type, amount, amount_usd, token))
            inserted += 1
        conn.commit()
        logger.info(f"Stored {inserted} transactions")
        for token in result:
            result[token] = [
                {
                    'date': date,
                    'buys': data['buys'],
                    'sells': data['sells'],
                    'buys_usd': data['buys_usd'],
                    'sells_usd': data['sells_usd']
                }
                for date, data in sorted(result[token].items())
            ]
        return result
    except Exception as e:
        logger.error(f"Failed to process transactions: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def update_wallets(entity_id, balances):
    """Update wallet balances in the database."""
    wallet_data = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for balance in balances:
            token = balance.get('symbol', balance.get('tokenSymbol', 'UNKNOWN')).upper()
            amount = float(balance.get('balance', 0))
            amount_usd = float(balance.get('usd', balance.get('usdValue', 0)))
            cursor.execute('''
                INSERT OR REPLACE INTO arkham_wallets (entity_id, token, balance, balance_usd, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (entity_id, token, amount, amount_usd, timestamp))
            wallet_data.append({
                'entity_id': entity_id,
                'token': token,
                'balance': amount,
                'balance_usd': amount_usd,
                'timestamp': timestamp
            })
        conn.commit()
        logger.info(f"Inserted {len(wallet_data)} wallet entries")
        return wallet_data
    except Exception as e:
        logger.error(f"Failed to update wallets: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def generate_visualizations(historical_balances, historical_total_balance, transactions, output_dir):
    """Generate visualizations for historical balances and transactions."""
    try:
        # Plot 1: Historical Total Balance
        dates = [datetime.strptime(entry['week_end'], '%Y-%m-%d') for entry in historical_total_balance]
        total_balances = [entry['total_balance_usd'] / 1e9 for entry in historical_total_balance]
        plt.figure(figsize=(12, 6))
        plt.plot(dates, total_balances, marker='o', label='Total Balance (USD Billions)')
        for event in FED_EVENTS:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if event_date in dates:
                idx = dates.index(event_date)
                plt.annotate(event['event'], (dates[idx], total_balances[idx]), textcoords="offset points", xytext=(0,10), ha='center')
        plt.title("BlackRock Historical Total Balance (USD)")
        plt.xlabel("Date")
        plt.ylabel("Balance (Billions USD)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "total_balance.png"))
        plt.close()
        logger.info("Generated total balance plot")

        # Plot 2: BTC, ETH, and USDC Balances
        plt.figure(figsize=(12, 6))
        for token in ['BTC', 'ETH', 'USDC']:
            if (token_data := historical_balances.get(token, [])):
                dates = [datetime.strptime(entry['week_end'], '%Y-%m-%d') for entry in token_data]
                balances = [entry['balance_usd'] / 1e9 for entry in token_data] if token == 'BTC' else [entry['balance'] for entry in token_data]
                plt.plot(dates, balances, marker='o', label=f"{token} {'Balance (Billions USD)' if token == 'BTC' else 'Balance'}")
        plt.title("BlackRock BTC, ETH, and USDC Balances")
        plt.xlabel("Date")
        plt.ylabel("Balance")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "btc_eth_usdc_balances.png"))
        plt.close()
        logger.info("Generated BTC/ETH/USDC balance plot")

        # Plot 3: Transaction Volumes (if available)
        if transactions:
            plt.figure(figsize=(12, 6))
            for token, tx_data in transactions.items():
                dates = [datetime.strptime(tx['date'], '%Y-%m-%d') for tx in tx_data]
                buys = [tx['buys_usd'] / 1e6 for tx in tx_data]
                sells = [tx['sells_usd'] / 1e6 for tx in tx_data]
                plt.plot(dates, buys, marker='o', label=f"{token} Buys (Millions USD)")
                plt.plot(dates, sells, marker='x', label=f"{token} Sells (Millions USD)")
            plt.title("BlackRock Transaction Volumes")
            plt.xlabel("Date")
            plt.ylabel("Volume (Millions USD)")
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "transaction_volumes.png"))
            plt.close()
            logger.info("Generated transaction volume plot")
    except Exception as e:
        logger.error(f"Failed to generate visualizations: {e}")

def analyze_insights(total_balance_usd, holdings_by_chain, transactions, historical_balances, historical_total_balance):
    """Generate AI-driven insights for market researchers."""
    insights = []
    try:
        btc_usd = holdings_by_chain.get('BTC', {}).get('balance_usd', 0)
        concentration = btc_usd / total_balance_usd * 100 if total_balance_usd > 0 else 0
        insights.append(f"BTC dominates BlackRock's crypto portfolio at {concentration:.2f}% of total USD value.")
        if not transactions:
            insights.append("No on-chain transactions detected for BlackRock in the period. Likely holding via custodial services (e.g., Coinbase Prime).")
        else:
            total_buys = sum(sum(tx['buys_usd'] for tx in tx_data) for tx_data in transactions.values())
            total_sells = sum(sum(tx['sells_usd'] for tx in tx_data) for tx_data in transactions.values())
            insights.append(f"Transaction activity: ${total_buys:,.2f} in buys, ${total_sells:,.2f} in sells.")
        btc_balances = [entry['balance'] for entry in historical_balances.get('BTC', [])]
        if btc_balances and all(abs(b - btc_balances[0]) < 1e-6 for b in btc_balances):
            insights.append("BTC holdings are stable, suggesting a long-term HODLing strategy.")
        else:
            insights.append("BTC holdings show variation, indicating active portfolio management.")
        for event in FED_EVENTS:
            event_date = event['date']
            for tx_data in transactions.values():
                insights.extend(
                    [
                        f"Transaction on {tx['date']} (${tx['buys_usd'] + tx['sells_usd']:,.2f} USD) near FED event: {event['event']}"
                        for tx in tx_data
                        if abs((datetime.strptime(tx['date'], '%Y-%m-%d') - datetime.strptime(event_date, '%Y-%m-%d')).days) <= 3
                    ]
                )
            insights.extend(
                [
                    f"Balance change on {balance['week_end']} (${balance['total_balance_usd']:,.2f}) near FED event: {event['event']}"
                    for balance in historical_total_balance
                    if abs((datetime.strptime(balance['week_end'], '%Y-%m-%d') - datetime.strptime(event_date, '%Y-%m-%d')).days) <= 7
                ]
            )
        if not transactions and all(abs((datetime.strptime(balance['week_end'], '%Y-%m-%d') - datetime.strptime(event['date'], '%Y-%m-%d')).days) > 7 for balance in historical_total_balance for event in FED_EVENTS):
            insights.append("No significant on-chain activity correlates with known FED events, suggesting BlackRock's crypto strategy is insulated from FED policy shifts.")
        return insights
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        return ["No insights generated due to data limitations."]

# REVISAR start_date, end_date, symbol, output_dir, output_data 
def main(start_date=None, end_date=None, symbol=None):
    """Main function to fetch and process BlackRock data using Arkham API."""
    logger.info("Starting blackrock.py")
    output_dir = user_log_dir("WhaleScope", "Cauco")
    output_data = {"type": "result", "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
    
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=223)).strftime('%Y-%m-%d')
        logger.info(f"Running from {start_date} to {end_date}{f' for {symbol}' if symbol else ''}")
        output_data["start_date"] = start_date
        output_data["end_date"] = end_date
        output_data["symbol"] = symbol

        init_db()
        if not check_api_key(ARKHAM_API_KEY):
            raise ValueError("Invalid API key")
        
        entity_data = fetch_blackrock_entity(ARKHAM_API_KEY)
        if not entity_data:
            raise ValueError("Failed to fetch BlackRock entity data")
        
        entity_id = entity_data.get('id', 'blackrock')
        entity_name = entity_data.get('name', 'BlackRock')
        tags = entity_data.get('populatedTags', [{"id": "fund", "label": "Fund"}])
        output_data["profile"] = {"name": entity_name, "tags": [tag['label'] for tag in tags]}
        
        api_balances = fetch_arkham_balances(ARKHAM_API_KEY, entity_id)
        if not api_balances:
            logger.warning("No balances fetched; proceeding with empty balances")
        output_data["balances"] = api_balances
        save_intermediate_output(output_dir, output_data, "blackrock_balances.json")
        
        wallet_data = update_wallets(entity_id, api_balances)
        output_data["wallet_data"] = wallet_data
        
        # Aggregate balances by token
        holdings_by_chain = {}
        aggregated_balances = {}
        for balance in api_balances:
            token = balance.get('symbol', '').upper()
            balance_amount = float(balance.get('balance', 0))
            balance_usd = float(balance.get('usd', 0))
            if token in aggregated_balances:
                aggregated_balances[token]['balance'] += balance_amount
                aggregated_balances[token]['usd'] += balance_usd
            else:
                aggregated_balances[token] = {'balance': balance_amount, 'usd': balance_usd}
            if token in ['BTC', 'ETH', 'USDC']:
                price = round(balance_usd / balance_amount, 2) if balance_amount > 0 else 1.0 if token == 'USDC' else 0.0
                holdings_by_chain[token] = {
                    'balance': aggregated_balances[token]['balance'],
                    'balance_usd': aggregated_balances[token]['usd'],
                    'price': price
                }
        # Initialize empty holdings if none exist
        for token in ['BTC', 'ETH', 'USDC']:
            if token not in holdings_by_chain:
                holdings_by_chain[token] = {'balance': 0.0, 'balance_usd': 0.0, 'price': 1.0 if token == 'USDC' else 0.0}
        output_data["holdings_by_chain"] = holdings_by_chain
        save_intermediate_output(output_dir, output_data, "blackrock_holdings.json")
        
        # Filter and aggregate balances for historical data
        balances = [
            {'symbol': token, 'balance': agg['balance'], 'usd': agg['usd']}
            for token, agg in aggregated_balances.items()
            if token in ['BTC', 'ETH', 'USDC']
        ]
        historical_prices = derive_prices_from_balances(api_balances, start_date, end_date)
        output_data["historical_prices"] = historical_prices
        save_intermediate_output(output_dir, output_data, "blackrock_prices.json")
        
        balances = ensure_historical_wallet_data(entity_id, start_date, end_date, balances, historical_prices)
        output_data["balances"] = balances
        
        # Fetch transactions
        raw_transactions = fetch_arkham_transactions(ARKHAM_API_KEY, entity_id, start_date, end_date, symbol)
        if not raw_transactions:
            logger.info("No entity transactions found, attempting address-based queries")
            if addresses := fetch_blackrock_addresses(ARKHAM_API_KEY, entity_id):
                for address in addresses[:20]:
                    raw_transactions.extend(fetch_address_transactions(ARKHAM_API_KEY, address, start_date, end_date, symbol))
                    time.sleep(1)
            else:
                logger.warning("No addresses found for entity blackrock, likely custodial holdings")
        
        transactions = process_transactions(raw_transactions, historical_prices, symbol)
        output_data["transactions"] = transactions
        save_intermediate_output(output_dir, output_data, "blackrock_transactions.json")
        
        exchange_usage = process_exchange_usage(raw_transactions, entity_id)
        output_data["exchange_usage"] = exchange_usage
        
        historical_balances = fetch_historical_balances(entity_id, start_date, end_date)
        output_data["historical_balances"] = historical_balances
        
        historical_total_balance = fetch_historical_total_balance(entity_id, start_date, end_date)
        output_data["historical_total_balance"] = historical_total_balance
        save_intermediate_output(output_dir, output_data, "blackrock_historical.json")
        
        # Safely calculate total balance
        total_balance_usd = sum(holdings_by_chain[token].get('balance_usd', 0) for token in holdings_by_chain)
        output_data["profile"]["total_balance_usd"] = total_balance_usd
        
        generate_visualizations(historical_balances, historical_total_balance, transactions, PLOT_DIR)
        
        insights = analyze_insights(total_balance_usd, holdings_by_chain, transactions, historical_balances, historical_total_balance)
        output_data["insights"] = insights
        
        output_file = os.path.join(output_dir, "blackrock_output.json")
        json_output = json.dumps(output_data, allow_nan=False)
        print(json_output)
        sys.stdout.flush()
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Data saved to {output_file}")
        
        return output_data
    except Exception as e:
        error = {"error": f"Failed to fetch BlackRock data: {str(e)}"}
        output_data["error"] = error["error"]
        logger.error(f"Error in main: {error['error']}")
        save_intermediate_output(output_dir, output_data, "blackrock_error.json")
        print(json.dumps(error))
        sys.stdout.flush()
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BlackRock data fetcher")
    parser.add_argument('--start-date', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument('--symbol', type=str, help="Token symbol (e.g., BTC, ETH, SOL)")
    args = parser.parse_args()
    main(args.start_date, args.end_date, args.symbol)