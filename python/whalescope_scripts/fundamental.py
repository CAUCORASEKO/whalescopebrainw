# fundamental.py

import requests
import sqlite3
from datetime import datetime
import urllib3
import os

# Desactivar advertencias de SSL (no recomendado, solo para fines académicos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Clave API de FRED
FRED_API_KEY = "ce4f47b6369b611995b2db9b6a5ee3d4"

# Fecha actual para filtrar datos
current_date = datetime.now()
current_date_str = current_date.strftime('%Y-%m-%d')

# Base de datos SQLite (ruta dinámica)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "whalescope.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS macro_events
                  (date TEXT, title TEXT, description TEXT, source TEXT, timestamp TEXT)''')
conn.commit()

# Función para recolectar datos de la FED desde FRED
def fetch_fed_data():
    fred_url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "FEDFUNDS",
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": "2020-01-01",
        "observation_end": current_date_str
    }
    
    try:
        response = requests.get(fred_url, params=params, verify=False, timeout=10)
        if response.status_code != 200:
            print(f"Error fetching FED data: {response.status_code}")
            return []
        
        data = response.json()
        observations = data.get("observations", [])
        
        # Procesar datos para detectar cambios en la tasa
        fed_events = []
        previous_value = None
        for obs in observations:
            date = obs["date"]
            if date > current_date_str:
                continue
            value = float(obs["value"])
            
            # Detectar cambios en la tasa
            if previous_value is not None and value != previous_value:
                fed_events.append({
                    "date": date,
                    "title": "FED Funds Rate Update",
                    "description": f"FED Funds Rate changed to {value}% (previous: {previous_value}%)",
                    "source": "FRED API"
                })
            previous_value = value
        
        print(f"Fetched {len(fed_events)} FED events")
        return fed_events
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []

# Recolectar y almacenar datos
fed_data = fetch_fed_data()
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if fed_data:
    for event in fed_data:
        # Guardar en SQLite con INSERT OR REPLACE para evitar duplicados
        cursor.execute("INSERT OR REPLACE INTO macro_events (date, title, description, source, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (event['date'], event['title'], event['description'], event['source'], timestamp))
    conn.commit()
    print("FED data saved to database")

# Cerrar conexión a SQLite
conn.close()