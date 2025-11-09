# clean_btc_prices.py

import sqlite3

conn = sqlite3.connect("whalescope.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM btc_prices")
conn.commit()
conn.close()
print("Tabla btc_prices limpiada.")