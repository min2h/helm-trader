from dataclasses import dataclass
from typing import Literal

from helm.config.schema import RiskLimits, RunState

CircuitAction = Literal["none", "soft_stop", "hard_kill"]


@dataclass(frozen=True)
class CircuitDecision:
    action: CircuitAction
    reason: str


def evaluate_circuit(
    *,
    daily_pnl_pct: float,
    drawdown_from_peak_pct: float,
    limits: RiskLimits,
    run_state: RunState,
) -> CircuitDecision:
    if run_state == "hard_kill":
        return CircuitDecision("none", "already_hard_kill")
    if drawdown_from_peak_pct >= limits.portfolio_mdd_kill_pct:
        return CircuitDecision("hard_kill", "portfolio_mdd")
    if daily_pnl_pct <= -limits.daily_loss_limit_pct:
        return CircuitDecision("soft_stop", "daily_loss_limit")
    return CircuitDecision("none", "")


def blocks_new_entry(equity: float, min_equity_usdt: float) -> bool:
    return min_equity_usdt > 0 and equity <= min_equity_usdt
