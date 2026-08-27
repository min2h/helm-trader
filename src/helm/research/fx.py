from __future__ import annotations

import time

from helm.research.http import first_json

_CACHE: tuple[float, float] | None = None
_TTL = 1800.0
_FALLBACK = 1350.0


def _parse_usd_krw(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    rates = payload.get("rates")
    if isinstance(rates, dict) and rates.get("KRW") is not None:
        value = float(rates["KRW"])
        return value if value > 0 else None
    if payload.get("usd_krw") is not None:
        value = float(payload["usd_krw"])
        return value if value > 0 else None
    return None


def usd_krw(timeout: float = 8.0) -> float:
    global _CACHE
    now = time.time()
    if _CACHE and now - _CACHE[0] < _TTL:
        return _CACHE[1]
    try:
        payload = first_json(
            [
                "https://open.er-api.com/v6/latest/USD",
                "https://api.frankfurter.app/latest?from=USD&to=KRW",
            ],
            timeout=timeout,
        )
        rate = _parse_usd_krw(payload) or _FALLBACK
    except Exception:
        rate = _FALLBACK
    _CACHE = (now, rate)
    return rate


def usdt_to_krw(usdt: float, rate: float | None = None) -> float:
    return float(usdt) * (rate if rate is not None else usd_krw())
