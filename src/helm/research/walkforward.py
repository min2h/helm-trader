from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from helm.research.donchian import BacktestResult, backtest_donchian


@dataclass(frozen=True)
class Fold:
    train: BacktestResult
    test: BacktestResult


def walk_forward(
    bars: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    **kwargs,
) -> list[Fold]:
    folds: list[Fold] = []
    start = 0
    while start + train_bars + test_bars <= len(bars):
        train = bars.iloc[start : start + train_bars]
        test = bars.iloc[start + train_bars : start + train_bars + test_bars]
        folds.append(
            Fold(
                train=backtest_donchian(train, **kwargs),
                test=backtest_donchian(test, **kwargs),
            )
        )
        start += test_bars
    return folds
