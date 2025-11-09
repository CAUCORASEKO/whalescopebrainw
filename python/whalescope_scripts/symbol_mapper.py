from datetime import date
from whalescope_scripts.binance_staking_tokens import SUPPORTED_STAKING_TOKENS

def normalize_symbol(symbol: str, query_date: date | None = None) -> str:
    """
    Devuelve el símbolo correcto según la fecha histórica.
    Ejemplo: si pides 'MATIC' en 2025, devuelve 'POL'.
    """

    s = symbol.upper()
    query_date = query_date or date.today()

    # --- Terra (LUNA / LUNC)
    if s in {"LUNA", "LUNC"}:
        if query_date < date(2022, 5, 15):
            return "LUNC"   # pre-crash (histórico de Terra Classic)
        elif s == "LUNC":
            return "LUNC"   # sigue siendo Terra Classic post-2022
        else:
            return "LUNA"   # nueva Terra 2.0

    # --- Polygon (MATIC → POL)
    if s in {"MATIC", "POL"}:
        if query_date < date(2024, 9, 1):
            return "MATIC"
        else:
            return "POL"

    # --- Zcoin (XZC → FIRO)
    if s in {"XZC", "FIRO"}:
        if query_date < date(2020, 10, 1):
            return "XZC"
        else:
            return "FIRO"

    # --- NEM / Symbol (XEM / XYM)
    if s in {"XEM", "XYM"}:
        if query_date < date(2021, 3, 15):
            return "XEM"    # antes del lanzamiento de Symbol
        else:
            return "XYM"    # Symbol network (nuevo)

    # --- Ethereum / Solana: mantener igual ---
    if s in {"ETH", "SOL"}:
        return s

    # Por defecto
    return s