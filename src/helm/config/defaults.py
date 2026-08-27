from helm.config.schema import RiskGrade, RiskLimits

RISK_PRESETS: dict[RiskGrade, RiskLimits] = {
    "conservative": RiskLimits(
        leverage=1,
        per_trade_risk_pct=0.5,
        daily_loss_limit_pct=2.0,
        portfolio_mdd_kill_pct=8.0,
        max_concurrent_positions=3,
    ),
    "standard": RiskLimits(
        leverage=2,
        per_trade_risk_pct=1.0,
        daily_loss_limit_pct=4.0,
        portfolio_mdd_kill_pct=15.0,
        max_concurrent_positions=5,
    ),
    "aggressive": RiskLimits(
        leverage=3,
        per_trade_risk_pct=2.0,
        daily_loss_limit_pct=6.0,
        portfolio_mdd_kill_pct=25.0,
        max_concurrent_positions=7,
    ),
}
