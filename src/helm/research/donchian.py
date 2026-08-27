from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from helm.risk.sizing import position_qty
from helm.strategies.signals import atr, donchian_signal, next_bar_entry


@dataclass(frozen=True)
class BacktestResult:
    trades: int
    win_rate: float
    total_return_pct: float
    max_drawdown_pct: float
    fees_paid: float
    equity_end: float
    bars: int


def _pnl(side: int, entry: float, exit_price: float, qty: float) -> float:
    return (exit_price - entry) * qty * (1 if side > 0 else -1)


def backtest_donchian(
    bars: pd.DataFrame,
    *,
    donchian_n: int = 20,
    atr_n: int = 14,
    atr_stop_mult: float = 2.0,
    take_r: float = 2.0,
    equity0: float = 10_000.0,
    risk_pct: float = 0.5,
    taker_fee: float = 0.0004,
    slippage_bps: float = 2.0,
) -> BacktestResult:
    """Event-style Donchian: signal on bar i, fill at bar i+1 open. Costs included."""
    if bars.empty:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, equity0, 0)

    frame = bars.reset_index(drop=True).copy()
    raw = donchian_signal(frame["high"], frame["low"], donchian_n)
    entries = next_bar_entry(raw)
    atr_series = atr(frame["high"], frame["low"], frame["close"], atr_n)

    equity = equity0
    peak = equity0
    max_dd = 0.0
    fees = 0.0
    wins = 0
    trades = 0
    side = 0
    qty = 0.0
    entry = 0.0
    stop = 0.0
    target = 0.0
    realized = 0.0
    scaled = False
    slip = slippage_bps / 10_000.0

    for i in range(len(frame)):
        o = float(frame.at[i, "open"])
        h = float(frame.at[i, "high"])
        low = float(frame.at[i, "low"])
        c = float(frame.at[i, "close"])

        if side != 0:
            hit_stop = low <= stop if side > 0 else h >= stop
            hit_target = (not scaled) and (h >= target if side > 0 else low <= target)
            if hit_stop:
                exit_price = stop * (1 - slip if side > 0 else 1 + slip)
                pnl = _pnl(side, entry, exit_price, qty)
                fee = abs(exit_price * qty) * taker_fee
                fees += fee
                equity += pnl - fee
                realized += pnl
                trades += 1
                if realized > 0:
                    wins += 1
                side = 0
                qty = 0.0
                realized = 0.0
                scaled = False
            elif hit_target:
                exit_price = target * (1 - slip if side > 0 else 1 + slip)
                exit_qty = qty * 0.5
                pnl = _pnl(side, entry, exit_price, exit_qty)
                fee = abs(exit_price * exit_qty) * taker_fee
                fees += fee
                equity += pnl - fee
                realized += pnl
                qty -= exit_qty
                scaled = True

        if side == 0 and int(entries.iat[i]) != 0 and pd.notna(atr_series.iat[i]):
            new_side = int(entries.iat[i])
            fill = o * (1 + slip if new_side > 0 else 1 - slip)
            stop_px = (
                fill - float(atr_series.iat[i]) * atr_stop_mult
                if new_side > 0
                else fill + float(atr_series.iat[i]) * atr_stop_mult
            )
            qty = position_qty(equity, risk_pct, fill, float(stop_px), leverage=1)
            if qty > 0:
                fee = abs(fill * qty) * taker_fee
                fees += fee
                equity -= fee
                side = new_side
                entry = fill
                stop = float(stop_px)
                risk_dist = abs(fill - stop)
                target = fill + take_r * risk_dist if new_side > 0 else fill - take_r * risk_dist
                realized = 0.0
                scaled = False

        mtm = equity
        if side != 0:
            mtm = equity + _pnl(side, entry, c, qty)
        peak = max(peak, mtm)
        if peak:
            max_dd = max(max_dd, (peak - mtm) / peak * 100)

    win_rate = wins / trades if trades else 0.0
    return BacktestResult(
        trades=trades,
        win_rate=win_rate,
        total_return_pct=(equity - equity0) / equity0 * 100,
        max_drawdown_pct=max_dd,
        fees_paid=fees,
        equity_end=equity,
        bars=len(frame),
    )
