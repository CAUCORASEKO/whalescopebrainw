# python/whalescope_scripts/binance_staking_tokens.py

"""
Listado oficial de tokens con soporte de staking en Binance.
Incluye símbolo, nombre y cadena nativa (para visualización en MarketBrain).
Actualizado a 2025 con soporte para ETH/SOL/On-chain/Soft Staking.
"""

BINANCE_STAKING_TOKENS = [
    # === Layer 1 Principales ===
    {"symbol": "ETH", "name": "Ethereum", "chain": "Ethereum Beacon"},
    {"symbol": "BNB", "name": "Binance Coin", "chain": "BNB Smart Chain"},
    {"symbol": "SOL", "name": "Solana", "chain": "Solana"},
    {"symbol": "ADA", "name": "Cardano", "chain": "Cardano"},
    {"symbol": "DOT", "name": "Polkadot", "chain": "Polkadot"},
    {"symbol": "AVAX", "name": "Avalanche", "chain": "Avalanche"},
    {"symbol": "ATOM", "name": "Cosmos Hub", "chain": "Cosmos"},
    {"symbol": "NEAR", "name": "NEAR Protocol", "chain": "NEAR"},
    {"symbol": "MATIC", "name": "Polygon", "chain": "Polygon"},
    {"symbol": "APT", "name": "Aptos", "chain": "Aptos"},
    {"symbol": "SUI", "name": "Sui", "chain": "Sui"},
    {"symbol": "FTM", "name": "Fantom", "chain": "Fantom"},
    {"symbol": "KSM", "name": "Kusama", "chain": "Kusama"},
    {"symbol": "TRX", "name": "TRON", "chain": "Tron"},
    {"symbol": "ICP", "name": "Internet Computer", "chain": "ICP"},
    {"symbol": "XTZ", "name": "Tezos", "chain": "Tezos"},
    {"symbol": "EGLD", "name": "MultiversX", "chain": "Elrond"},
    {"symbol": "ONE", "name": "Harmony", "chain": "Harmony"},
    {"symbol": "CELO", "name": "Celo", "chain": "Celo"},
    {"symbol": "OSMO", "name": "Osmosis", "chain": "Cosmos"},

    # === Tokens derivados de Staking ===
    {"symbol": "BETH", "name": "Beacon ETH", "chain": "Ethereum Beacon"},
    {"symbol": "WBETH", "name": "Wrapped Beacon ETH", "chain": "Ethereum Beacon"},
    {"symbol": "BNSOL", "name": "Binance SOL", "chain": "Solana"},
    {"symbol": "SOLV", "name": "Solv Protocol", "chain": "BNB Smart Chain"},

    # === Stablecoins comunes en On-chain Yields ===
    {"symbol": "USDT", "name": "Tether USD", "chain": "Multi-chain"},
    {"symbol": "USDC", "name": "USD Coin", "chain": "Multi-chain"},
    {"symbol": "FDUSD", "name": "First Digital USD", "chain": "BNB Smart Chain"},
]

# 🔹 Lista rápida de símbolos para validación en el fetcher
SUPPORTED_STAKING_TOKENS = [t["symbol"] for t in BINANCE_STAKING_TOKENS]