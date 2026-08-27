from __future__ import annotations

from pathlib import Path

import pandas as pd

from helm.research.http import first_json

SPOT_KLINES = "https://api.binance.com/api/v3/klines"
FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"
VISION_KLINES = "https://data-api.binance.vision/api/v3/klines"
SPOT_PRICE = "https://api.binance.com/api/v3/ticker/price"
FUTURES_PRICE = "https://fapi.binance.com/fapi/v1/ticker/price"
VISION_PRICE = "https://data-api.binance.vision/api/v3/ticker/price"


def fetch_klines(
    symbol: str,
    interval: str = "15m",
    *,
    limit: int = 1000,
    market: str = "futures",
    timeout: float = 20.0,
) -> pd.DataFrame:
    urls = [FUTURES_KLINES, SPOT_KLINES, VISION_KLINES] if market == "futures" else [SPOT_KLINES, VISION_KLINES]
    rows = first_json(
        urls,
        params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
        timeout=timeout,
    )
    if not isinstance(rows, list):
        raise RuntimeError("unexpected klines payload")
    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = frame[col].astype(float)
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    return frame[["open_time", "open", "high", "low", "close", "volume"]]


def fetch_last_price(symbol: str, market: str = "futures", timeout: float = 8.0) -> dict:
    urls = [FUTURES_PRICE, SPOT_PRICE, VISION_PRICE] if market == "futures" else [SPOT_PRICE, VISION_PRICE]
    row = first_json(urls, params={"symbol": symbol.upper()}, timeout=timeout)
    return {"symbol": str(row.get("symbol") or symbol).upper(), "price": float(row["price"])}


def save_klines(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def load_klines(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)
