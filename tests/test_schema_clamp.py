from helm.config.schema import Params, clamp_params, merge_ai_patches


def test_leverage_over_cap_rejected() -> None:
    result = clamp_params({"risk": {"leverage": 20}})
    assert "risk.leverage" in result.rejected
    assert result.params.risk.leverage == 1


def test_donchian_clamped() -> None:
    result = clamp_params({"strategy": {"trend": {"donchian_n": 3, "atr_stop_mult": 9}}})
    assert result.params.strategy.trend.donchian_n == 10
    assert result.params.strategy.trend.atr_stop_mult == 4.0


def test_ai_cannot_change_locked_fields() -> None:
    current = Params()
    result = merge_ai_patches(
        current,
        {
            "run_state": "hard_kill",
            "risk_grade": "aggressive",
            "market_mode": "spot",
            "strategy.trend.donchian_n": 24,
            "risk.leverage": 3,
        },
    )
    assert result.params.run_state == "running"
    assert result.params.risk_grade == "conservative"
    assert result.params.market_mode == "futures"
    assert result.params.strategy.trend.donchian_n == 24
    assert "run_state" in result.rejected
    assert "risk.leverage" in result.rejected
