from __future__ import annotations

import logging
from datetime import datetime, timezone

from helm.db.store import Database
from helm.research.http import first_json

log = logging.getLogger(__name__)

SPOT_INFO = "https://api.binance.com/api/v3/exchangeInfo"
FUTURES_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
VISION_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
STALE_SEC = 6 * 3600


def catalog_from_exchange_info(payload: dict, market: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for raw in payload.get("symbols") or []:
        status = str(raw.get("status") or "").upper()
        if status not in {"TRADING", ""}:
            continue
        if market == "futures" and raw.get("contractType") not in {None, "PERPETUAL"}:
            continue
        symbol = str(raw.get("symbol") or "").upper()
        quote = str(raw.get("quoteAsset") or "").upper()
        base = str(raw.get("baseAsset") or "").upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(
            {
                "symbol": symbol,
                "base": base or symbol.replace(quote, ""),
                "quote": quote or "USDT",
                "market": market,
                "status": "TRADING",
            }
        )
    out.sort(key=lambda item: (item["quote"] != "USDT", item["symbol"]))
    return out


def fetch_full_catalog(timeout: float = 20.0) -> list[dict]:
    items: list[dict] = []
    try:
        items.extend(catalog_from_exchange_info(first_json([SPOT_INFO, VISION_INFO], timeout=timeout), "spot"))
    except Exception as exc:
        log.warning("spot catalog missed: %s", exc)
    try:
        items.extend(catalog_from_exchange_info(first_json([FUTURES_INFO], timeout=timeout), "futures"))
    except Exception as exc:
        log.warning("futures catalog missed: %s", exc)
    return items


def _age_sec(stamp: str | None) -> float | None:
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(stamp)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - when).total_seconds())
    except ValueError:
        return None


def load_catalog(db: Database, market: str = "all", *, refresh: bool = False) -> dict:
    count = db.market_symbol_count()
    age = _age_sec(db.market_symbols_updated_at())
    stale = age is None or age > STALE_SEC
    if refresh or count == 0 or stale:
        fetched = fetch_full_catalog()
        if fetched:
            count = db.replace_market_symbols(fetched)
    symbols = db.list_market_symbols(market)
    return {
        "market": market,
        "count": db.market_symbol_count(market),
        "updated_at": db.market_symbols_updated_at(),
        "symbols": symbols,
        "source": "db" if symbols else None,
    }
