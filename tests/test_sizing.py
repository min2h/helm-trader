from helm.risk.circuit import evaluate_circuit
from helm.risk.sizing import position_qty
from helm.config.schema import RiskLimits


def test_qty_caps_loss_to_risk_budget() -> None:
    qty = position_qty(10_000, 1.0, 100.0, 99.0, leverage=1)
    assert abs(qty * 1.0 - 100.0) < 1e-9


def test_qty_respects_leverage_notional() -> None:
    qty = position_qty(1_000, 2.0, 100.0, 99.9, leverage=1)
    assert qty * 100.0 <= 1_000 + 1e-9


def test_daily_loss_soft_stops() -> None:
    decision = evaluate_circuit(
        daily_pnl_pct=-2.5,
        drawdown_from_peak_pct=1.0,
        limits=RiskLimits(),
        run_state="running",
    )
    assert decision.action == "soft_stop"


def test_mdd_hard_kills() -> None:
    decision = evaluate_circuit(
        daily_pnl_pct=-0.1,
        drawdown_from_peak_pct=8.0,
        limits=RiskLimits(),
        run_state="running",
    )
    assert decision.action == "hard_kill"
