from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

Side = Literal["long", "short", "flat"]


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    return true_range(high, low, close).rolling(n, min_periods=n).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(high, low, close)
    atr_n = tr.rolling(n, min_periods=n).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).rolling(n, min_periods=n).mean() / atr_n
    minus_di = 100 * pd.Series(minus_dm, index=high.index).rolling(n, min_periods=n).mean() / atr_n
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.rolling(n, min_periods=n).mean()


def donchian_signal(high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    """+1 breakout long, -1 breakout short, 0 otherwise. Uses prior N bars only."""
    upper = high.shift(1).rolling(n, min_periods=n).max()
    lower = low.shift(1).rolling(n, min_periods=n).min()
    signal = pd.Series(0, index=high.index, dtype=int)
    signal = signal.mask(high > upper, 1)
    signal = signal.mask(low < lower, -1)
    return signal.fillna(0).astype(int)


def next_bar_entry(signal: pd.Series) -> pd.Series:
    """Enter on the next bar to avoid look-ahead on the signal bar close."""
    return signal.shift(1).fillna(0).astype(int)
