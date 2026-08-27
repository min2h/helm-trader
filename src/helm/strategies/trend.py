"""Trend strategy. Signal functions live in signals.py.

A Nautilus Strategy subclass is added in Phase 2. This module documents the
live contract without importing nautilus_trader at process start.
"""

from dataclasses import dataclass

from helm.config.schema import TrendParams
from helm.risk.exchange_stops import close_position_stop


@dataclass(frozen=True)
class TrendIntent:
    side: str
    stop_price: float
    exchange_stop: dict


def build_entry_stop(
    *,
    symbol: str,
    side: str,
    entry_price: float,
    atr_value: float,
    params: TrendParams,
) -> TrendIntent:
    if side == "BUY":
        stop = entry_price - atr_value * params.atr_stop_mult
    else:
        stop = entry_price + atr_value * params.atr_stop_mult
    return TrendIntent(
        side=side,
        stop_price=stop,
        exchange_stop=close_position_stop(symbol=symbol, side=side, trigger_price=stop),
    )
