import numpy as np
import pandas as pd

from helm.research.donchian import backtest_donchian
from helm.strategies.signals import donchian_signal, next_bar_entry


def _synthetic(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    price = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
    high = price + 0.6
    low = price - 0.6
    return pd.DataFrame(
        {
            "open_time": pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"),
            "open": price,
            "high": high,
            "low": low,
            "close": price,
            "volume": 1.0,
        }
    )


def test_signal_uses_prior_window_only() -> None:
    bars = _synthetic(40)
    signal = donchian_signal(bars["high"], bars["low"], 10)
    assert signal.iloc[:10].sum() == 0


def test_entry_is_next_bar() -> None:
    signal = pd.Series([0, 1, 0, -1])
    assert list(next_bar_entry(signal)) == [0, 0, 1, 0]


def test_backtest_includes_fees_and_finishes() -> None:
    result = backtest_donchian(_synthetic(), taker_fee=0.0004, slippage_bps=2)
    assert result.bars == 200
    assert result.fees_paid >= 0
    assert result.equity_end > 0
