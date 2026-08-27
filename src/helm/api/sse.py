from helm.actors.control_actor import ControlActor


def status_payload(actor: ControlActor) -> dict:
    params = actor.params()
    runtime = actor.status()
    return {
        "run_state": params.run_state,
        "strategy_mode": params.strategy_mode,
        "risk_grade": params.risk_grade,
        "market_mode": params.market_mode,
        "ai_level": params.ai_level,
        "ai_last_status": params.ai.last_status,
        "active_symbols": params.symbols.active,
        "pending_symbols": params.symbols.pending_approval,
        "daily_pnl_pct": runtime.daily_pnl_pct,
        "drawdown_from_peak_pct": runtime.drawdown_from_peak_pct,
        "open_positions": runtime.open_positions,
        "heartbeat_at": runtime.heartbeat_at.isoformat() if runtime.heartbeat_at else None,
        "last_command": (
            {
                "kind": runtime.last_command.kind,
                "reason": runtime.last_command.reason,
                "at": runtime.last_command.at.isoformat(),
            }
            if runtime.last_command
            else None
        ),
    }
