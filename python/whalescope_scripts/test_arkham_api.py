import requests
import logging
import time
from datetime import datetime
import sys
import json

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='test_arkham_api.log',
    filemode='a'
)

# API Key
ARKHAM_API_KEY = "2ee4d166-eb6f-40a9-b89e-d061a8a328a1"

def check_api_key(api_key):
    """Verifica si la clave API de Arkham es válida usando el endpoint /health."""
    base_url = "https://api.arkm.com"
    endpoint = f"{base_url}/health"
    headers = {
        "API-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "WhaleScope/1.0 (TestScript)"
    }
    try:
        logging.info(f"Checking API key validity at {endpoint}")
        logging.debug(f"Headers: {headers}")
        response = requests.get(endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"API key is valid. Response: {response.text}")
        return True
    except requests.RequestException as e:
        error_message = f"Failed to validate API key: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
        logging.error(error_message)
        return False




def fetch_blackrock_entity(api_key):
    """Obtiene información de la entidad BlackRock desde Arkham Intelligence."""
    base_url = "https://api.arkm.com"
    endpoint = f"{base_url}/intelligence/entity/blackrock"
    headers = {
        "API-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "WhaleScope/1.0 (BlackRockScript)"
    }
    try:
        logging.info(f"Fetching BlackRock entity data from {endpoint}")
        time.sleep(0.1)  # Add delay to avoid potential rate limiting
        response = requests.get(endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Raw API response: {data}")
        entity_id = data.get('id')  # Changed from 'entity_id' to 'id'
        if not entity_id:
            logging.error("No id found in BlackRock entity data")
            return None
        logging.info(f"Successfully fetched BlackRock entity data: {data}")
        return data
    except requests.RequestException as e:
        error_message = f"Failed to fetch BlackRock entity data: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
            if e.response.status_code == 401:
                error_message += " | Please verify your API key at https://info.arkm.com/api-platform"
        logging.error(error_message)
        return None





def fetch_transactions(api_key, entity_id, start_date, end_date):
    """Obtiene transacciones históricas para una entidad."""
    base_url = "https://api.arkm.com"
    url = f"{base_url}/history/entity/{entity_id}"
    headers = {
        "API-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "WhaleScope/1.0 (TestScript)"
    }
    # Convertir fechas a timestamps
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    params = {
        "startDate": int(start.timestamp()),
        "endDate": int(end.timestamp()),
        "limit": 10  # Limitamos a 10 transacciones para la prueba
    }
    try:
        logging.info(f"Fetching transactions for entity {entity_id} from {start_date} to {end_date}")
        time.sleep(0.05)  # Respetar el límite de tasa (20 req/sec)
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        transactions = data.get('transfers', data.get('transactions', []))
        logging.info(f"Fetched {len(transactions)} transactions: {transactions}")
        return transactions
    except requests.RequestException as e:
        error_message = f"Failed to fetch transactions: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
        logging.error(error_message)
        return []

def main():
    """Función principal para probar la API de Arkham Intelligence."""
    try:
        # Paso 1: Verificar la clave API
        if not check_api_key(ARKHAM_API_KEY):
            raise Exception("Invalid API key. Please verify your API key at https://info.arkm.com/api-platform or contact Arkham support.")

        # Paso 2: Obtener datos de la entidad BlackRock
        entity_data = fetch_blackrock_entity(ARKHAM_API_KEY)
        if not entity_data:
            raise Exception("Failed to fetch BlackRock entity data")

        entity_id = entity_data.get('entity_id')
        if not entity_id:
            raise Exception("No entity_id found in BlackRock entity data")

        logging.info(f"BlackRock entity_id: {entity_id}")

        # Paso 3: Obtener transacciones históricas
        start_date = "2025-04-03"
        end_date = "2025-05-03"
        transactions = fetch_transactions(ARKHAM_API_KEY, entity_id, start_date, end_date)

        # Imprimir resultados
        result = {
            "status": "success",
            "entity_id": entity_id,
            "transactions_count": len(transactions),
            "transactions_sample": transactions[:3] if transactions else [],
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        print(# The `json` module in Python is used for encoding and decoding JSON data. In the
        # provided code snippet, the `json` module is being used to format Python dictionaries
        # into a JSON string for printing the results of the API calls in a more readable and
        # structured way.
        json.dumps(result, indent=2))
        logging.info("Test completed successfully")

    except Exception as e:
        error = {"status": "error", "message": str(e)}
        logging.error(str(e))
        print(json.dumps(error, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()