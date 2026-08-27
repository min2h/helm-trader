from __future__ import annotations

from helm.research.http import first_json

STABLES = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "DAIUSDT", "USDPUSDT"}


def fetch_usdt_tickers(market: str = "futures", timeout: float = 20.0) -> list[dict]:
    urls = [
        "https://fapi.binance.com/fapi/v1/ticker/24hr",
        "https://api.binance.com/api/v3/ticker/24hr",
        "https://data-api.binance.vision/api/v3/ticker/24hr",
    ]
    if market != "futures":
        urls = urls[1:]
    return first_json(urls, timeout=timeout)


def screen_symbols(
    tickers: list[dict],
    *,
    blacklist: list[str],
    top_n: int = 40,
) -> list[str]:
    blocked = {s.upper() for s in blacklist} | STABLES
    scored: list[tuple[float, str]] = []
    for row in tickers:
        symbol = str(row.get("symbol", "")).upper()
        if not symbol.endswith("USDT") or symbol in blocked:
            continue
        volume = float(row.get("quoteVolume") or 0)
        scored.append((volume, symbol))
    scored.sort(reverse=True)
    return [symbol for _, symbol in scored[:top_n]]
