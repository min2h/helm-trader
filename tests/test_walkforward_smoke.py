import numpy as np
import pandas as pd

from helm.research.walkforward import walk_forward


def test_walk_forward_emits_folds() -> None:
    n = 80
    price = np.linspace(100, 110, n)
    bars = pd.DataFrame(
        {
            "open": price,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1.0,
        }
    )
    folds = walk_forward(bars, train_bars=30, test_bars=15)
    assert folds
    assert folds[0].test.bars == 15
