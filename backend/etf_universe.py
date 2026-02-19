# backend/etf_universe.py

ETF_UNIVERSE_V1 = [
    # Core index ETFs
    "SPY", "QQQ", "IWM", "DIA",

    # Sector SPDRs
    "XLE", "XLF", "XLK", "XLI", "XLP", "XLY",
    "XLV", "XLB", "XLU", "XLRE",
]

def get_etf_universe():
    return ETF_UNIVERSE_V1[:]
