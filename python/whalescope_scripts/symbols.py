# ============================================================
# symbols.py
# Diccionario maestro de símbolos y alias normalizados
# ============================================================

# === Soportados en Allium (7 chains disponibles) ===
CHAIN_MAP = {
    "aptos": "APTOS",
    "bsc": "BNB", "binance-sc": "BNB", "binance": "BNB", "bnb": "BNB",
    "ethereum": "ETH", "eth": "ETH", "eth2": "ETH", "eth2.0": "ETH",
    "near": "NEAR",
    "polygon": "POL", "matic": "POL", "pol": "POL",
    "sui": "SUI",
    "ton": "TON",
}

# === Lista extendida de Ville (no soportada aún en Allium) ===
# Se deja comentada para activar luego con otras fuentes (ej. Dune)

"""
    "0x": "ZRX", "zrx": "ZRX",
    "1inch": "1INCH", "1inch-exchange": "1INCH",
    "aave": "AAVE",
    "aion": "AION",
    "algorand": "ALGO", "algo": "ALGO",
    "ark": "ARK",
    "avalanche": "AVAX", "avax": "AVAX",
    "band": "BAND",
    "beefy": "BIFI", "bifi": "BIFI",
    "bitbay": "BAY", "bay": "BAY",
    "cardano": "ADA", "ada": "ADA",
    "celo": "CELO",
    "cosmos": "ATOM", "atom": "ATOM",
    "cronos": "CRO", "cro": "CRO",
    "curve": "CRV", "crv": "CRV",
    "dash": "DASH",
    "decred": "DCR",
    "dfinity": "ICP", "icp": "ICP",
    "dodo": "DODO",
    "dydx": "DYDX",
    "elrond": "EGLD", "multiversx": "EGLD",
    "eos": "EOS",
    "fantom": "FTM",
    "flow": "FLOW",
    "harmony": "ONE",
    "icon": "ICX",
    "idex": "IDEX",
    "injective": "INJ",
    "iotex": "IOTX",
    "iris": "IRIS",
    "kava": "KAVA",
    "kusama": "KSM",
    "kyber": "KNC",
    "livepeer": "LPT",
    "lto": "LTO",
    "mina": "MINA",
    "mirror": "MIR",
    # NEM + Symbol
    "nem": "XEM",
    "symbol": "XYM",
    "neo": "NEO",
    "nuls": "NULS",
    "oasis": "ROSE",
    "olympus": "OHM",
    "osmosis": "OSMO",
    "pancakeswap": "CAKE",
    "peakdefi": "PEAK",
    "polkadot": "DOT",
    "qtum": "QTUM",
    "secret": "SCRT",
    "smartcash": "SMART",
    "snx": "SNX",
    "sol": "SOL", "solana": "SOL",
    "stafi": "FIS",
    "stake-dao": "SDT",
    "sushi": "SUSHI",
    # Terra collapse
    "terra": "LUNA",
    "luna": "LUNA",   # Terra 2.0
    "lunc": "LUNC",   # Terra Classic
    "terra-classic": "LUNC",
    "tezos": "XTZ",
    "tron": "TRX",
    "wanchain": "WAN",
    "waves": "WAVES",
    "wax": "WAXP",
    "yearn": "YFI",
    # Zcoin rebrand
    "zcoin": "FIRO", "xzc": "FIRO", "firo": "FIRO",
"""