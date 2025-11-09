import sqlite3
import plotly.graph_objects as go
import pandas as pd
import logging
from datetime import datetime
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plot_balances.log')
    ]
)

# Ruta a la base de datos
DB_PATH = '/Users/mestizo/Desktop/whalescope/WhaleScope/whalescope.db'

def query_balances():
    """Query historical BTC and ETH balances from whalescope.db."""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT token, balance, balance_usd, timestamp
        FROM arkham_wallets
        WHERE entity_id = 'blackrock' AND token IN ('BTC', 'ETH')
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        logging.info(f"Queried {len(df)} balance entries from database")
        return df
    except Exception as e:
        logging.error(f"Failed to query balances: {e}")
        return pd.DataFrame()

def plot_balance(token, df):
    """Generate a line chart for the given token's balance over time."""
    try:
        # Filter data for the token
        token_df = df[df['token'] == token]
        if token_df.empty:
            logging.warning(f"No data found for {token}")
            return

        # Create Plotly figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=token_df['timestamp'],
            y=token_df['balance'],
            mode='lines+markers',
            name=f'{token} Balance'
        ))

        # Update layout
        fig.update_layout(
            title=f'{token} Balance Over Time for BlackRock',
            xaxis_title='Timestamp',
            yaxis_title=f'{token} Balance',
            xaxis=dict(tickangle=45),
            showlegend=True
        )

        # Save as HTML
        output_file = f'{token.lower()}_balance.html'
        fig.write_html(output_file, auto_open=False)
        logging.info(f"Saved {token} balance chart to {output_file}")
    except Exception as e:
        logging.error(f"Failed to plot {token} balance: {e}")

def main():
    logging.info("Starting plot_balances.py")
    try:
        # Query balances
        df = query_balances()
        if df.empty:
            logging.error("No balance data found. Exiting.")
            return

        # Plot BTC and ETH balances
        plot_balance('BTC', df)
        plot_balance('ETH', df)

        logging.info("Plotting completed successfully")
    except Exception as e:
        logging.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()