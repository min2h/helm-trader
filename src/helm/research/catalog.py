from __future__ import annotations

import time

import httpx

SPOT_INFO = "https://api.binance.com/api/v3/exchangeInfo"
FUTURES_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"

FALLBACK = [
    {"symbol": "BTCUSDT", "base": "BTC", "quote": "USDT", "market": "futures"},
    {"symbol": "ETHUSDT", "base": "ETH", "quote": "USDT", "market": "futures"},
    {"symbol": "SOLUSDT", "base": "SOL", "quote": "USDT", "market": "futures"},
    {"symbol": "XRPUSDT", "base": "XRP", "quote": "USDT", "market": "futures"},
    {"symbol": "BNBUSDT", "base": "BNB", "quote": "USDT", "market": "futures"},
    {"symbol": "DOGEUSDT", "base": "DOGE", "quote": "USDT", "market": "futures"},
    {"symbol": "ADAUSDT", "base": "ADA", "quote": "USDT", "market": "futures"},
    {"symbol": "AVAXUSDT", "base": "AVAX", "quote": "USDT", "market": "futures"},
    {"symbol": "LINKUSDT", "base": "LINK", "quote": "USDT", "market": "futures"},
    {"symbol": "SUIUSDT", "base": "SUI", "quote": "USDT", "market": "futures"},
]

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_TTL_SEC = 3600.0


def catalog_from_exchange_info(payload: dict, market: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for raw in payload.get("symbols") or []:
        if raw.get("status") not in {"TRADING", "trading"}:
            continue
        if raw.get("quoteAsset") != "USDT":
            continue
        if market == "futures" and raw.get("contractType") not in {None, "PERPETUAL"}:
            continue
        symbol = str(raw.get("symbol") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(
            {
                "symbol": symbol,
                "base": str(raw.get("baseAsset") or symbol.replace("USDT", "")),
                "quote": "USDT",
                "market": market,
            }
        )
    out.sort(key=lambda item: item["symbol"])
    return out


def fetch_usdt_catalog(market: str = "futures", timeout: float = 12.0) -> list[dict]:
    key = market if market in {"spot", "futures"} else "futures"
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _TTL_SEC:
        return cached[1]
    url = FUTURES_INFO if key == "futures" else SPOT_INFO
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        items = catalog_from_exchange_info(response.json(), key)
    except Exception:
        items = [dict(row, market=key) for row in FALLBACK]
    if not items:
        items = [dict(row, market=key) for row in FALLBACK]
    _CACHE[key] = (now, items)
    return items
