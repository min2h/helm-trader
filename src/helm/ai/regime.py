from __future__ import annotations

from typing import Literal

import pandas as pd

from helm.strategies.signals import adx

Regime = Literal["trend", "range", "high_vol_chop", "unknown"]


def classify_regime(bars: pd.DataFrame, adx_n: int = 14) -> Regime:
    if len(bars) < adx_n * 3:
        return "unknown"
    latest = float(adx(bars["high"], bars["low"], bars["close"], adx_n).iloc[-1])
    ret = bars["close"].pct_change().dropna()
    vol = float(ret.tail(20).std()) if len(ret) >= 20 else 0.0
    vol_rank = float((ret.rolling(20).std().rank(pct=True)).iloc[-1]) if len(ret) >= 40 else 0.5
    if latest >= 25 and vol_rank >= 0.4:
        return "trend"
    if latest < 18 and vol_rank >= 0.8:
        return "high_vol_chop"
    if latest < 18:
        return "range"
    return "trend" if vol > 0 else "unknown"
