from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd

SPOT_KLINES = "https://api.binance.com/api/v3/klines"
FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"


def fetch_klines(
    symbol: str,
    interval: str = "15m",
    *,
    limit: int = 1000,
    market: str = "futures",
    timeout: float = 20.0,
) -> pd.DataFrame:
    url = FUTURES_KLINES if market == "futures" else SPOT_KLINES
    response = httpx.get(
        url,
        params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
        timeout=timeout,
    )
    response.raise_for_status()
    rows = response.json()
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


def save_klines(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def load_klines(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)
