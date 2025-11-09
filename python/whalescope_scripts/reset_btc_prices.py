
# reset_btc_prices.py

import sqlite3

conn = sqlite3.connect("whalescope.db")
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS btc_prices")
cursor.execute('''CREATE TABLE btc_prices
                  (date TEXT, price_usd REAL, volume_usd REAL, ticker TEXT, timestamp TEXT)''')
conn.commit()
conn.close()
print("Tabla btc_prices recreada con nueva estructura.")