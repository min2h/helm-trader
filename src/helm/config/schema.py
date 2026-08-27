from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

MarketMode = Literal["spot", "futures", "both"]
SymbolSelection = Literal["ai_auto", "manual", "ai_approve"]
StrategyMode = Literal["trend", "funding_arb", "grid", "regime_auto"]
RiskGrade = Literal["conservative", "standard", "aggressive"]
AiLevel = Literal["off", "params_only", "params_and_symbols"]
StopStyle = Literal["fixed_pct", "atr", "trailing"]
RunState = Literal["running", "soft_stop", "hard_kill"]
UpdatedBy = Literal["user", "ai_batch", "system"]

AI_LOCKED_FIELDS = frozenset({"run_state", "risk_grade", "market_mode"})

AI_PATCH_WHITELIST = frozenset(
    {
        "strategy.trend.donchian_n",
        "strategy.trend.atr_n",
        "strategy.trend.atr_stop_mult",
        "strategy.trend.min_adx",
        "strategy.trend.timeframe",
        "strategy.funding_arb.min_funding_apr",
        "strategy.funding_arb.max_basis_bps",
        "strategy.funding_arb.rebalance_threshold_bps",
        "strategy.grid.grid_atr_mult",
        "strategy.grid.levels",
        "strategy.grid.max_inventory_pct",
        "strategy.grid.timeframe",
        "risk.per_trade_risk_pct",
        "risk.daily_loss_limit_pct",
        "risk.portfolio_mdd_kill_pct",
        "symbols.pending_approval",
    }
)

USER_PATCH_FIELDS = frozenset(
    {
        "market_mode",
        "symbol_selection",
        "strategy_mode",
        "risk_grade",
        "ai_level",
        "stop_style",
        "run_state",
        "symbols.active",
        "symbols.blacklist",
        "risk.min_equity_usdt",
    }
)


class Symbols(BaseModel):
    active: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    pending_approval: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(default_factory=lambda: ["USDCUSDT"])

    @field_validator("active", "pending_approval", "blacklist")
    @classmethod
    def upper_unique(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in value:
            symbol = raw.strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            out.append(symbol)
        return out

    @field_validator("active")
    @classmethod
    def cap_active(cls, value: list[str]) -> list[str]:
        if len(value) > 20:
            raise ValueError("symbols.active cannot exceed 20")
        return value


class TrendParams(BaseModel):
    timeframe: str = "15m"
    donchian_n: int = 20
    atr_n: int = 14
    atr_stop_mult: float = 2.0
    min_adx: float = 20.0

    @model_validator(mode="after")
    def clamp_fields(self) -> Self:
        self.donchian_n = int(_clamp(self.donchian_n, 10, 60))
        self.atr_n = int(_clamp(self.atr_n, 5, 40))
        self.atr_stop_mult = _clamp(self.atr_stop_mult, 1.0, 4.0)
        self.min_adx = _clamp(self.min_adx, 10.0, 40.0)
        return self


class FundingArbParams(BaseModel):
    min_funding_apr: float = 0.10
    max_basis_bps: float = 15.0
    rebalance_threshold_bps: float = 25.0

    @model_validator(mode="after")
    def clamp_fields(self) -> Self:
        self.min_funding_apr = _clamp(self.min_funding_apr, 0.02, 0.50)
        self.max_basis_bps = _clamp(self.max_basis_bps, 5.0, 80.0)
        self.rebalance_threshold_bps = _clamp(self.rebalance_threshold_bps, 10.0, 100.0)
        return self


class GridParams(BaseModel):
    timeframe: str = "5m"
    grid_atr_mult: float = 0.4
    levels: int = 6
    max_inventory_pct: float = 30.0

    @model_validator(mode="after")
    def clamp_fields(self) -> Self:
        self.grid_atr_mult = _clamp(self.grid_atr_mult, 0.15, 1.5)
        self.levels = int(_clamp(self.levels, 3, 12))
        self.max_inventory_pct = _clamp(self.max_inventory_pct, 10.0, 60.0)
        return self


class StrategyParams(BaseModel):
    trend: TrendParams = Field(default_factory=TrendParams)
    funding_arb: FundingArbParams = Field(default_factory=FundingArbParams)
    grid: GridParams = Field(default_factory=GridParams)


class ManualBand(BaseModel):
    symbol: str = "BTCUSDT"
    lower: float = 0.0
    upper: float = 0.0
    schedule: str = "every_15m"
    size_usdt: float = 100.0

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, value: str) -> str:
        return value.strip().upper() or "BTCUSDT"

    @model_validator(mode="after")
    def clamp_fields(self) -> Self:
        self.size_usdt = max(10.0, min(self.size_usdt, 100_000.0))
        if self.lower and self.upper and self.lower >= self.upper:
            raise ValueError("manual_band.lower must be below upper")
        return self


class RiskLimits(BaseModel):
    leverage: int = 1
    per_trade_risk_pct: float = 0.5
    daily_loss_limit_pct: float = 2.0
    portfolio_mdd_kill_pct: float = 8.0
    max_concurrent_positions: int = 3
    min_equity_usdt: float = 0.0

    @field_validator("leverage")
    @classmethod
    def leverage_hard_cap(cls, value: int) -> int:
        if value < 1 or value > 3:
            raise ValueError("risk.leverage must be 1..3")
        return value

    @model_validator(mode="after")
    def clamp_fields(self) -> Self:
        self.per_trade_risk_pct = _clamp(self.per_trade_risk_pct, 0.1, 2.0)
        self.daily_loss_limit_pct = _clamp(self.daily_loss_limit_pct, 1.0, 8.0)
        self.portfolio_mdd_kill_pct = _clamp(self.portfolio_mdd_kill_pct, 5.0, 30.0)
        self.max_concurrent_positions = int(_clamp(self.max_concurrent_positions, 1, 7))
        self.min_equity_usdt = max(0.0, float(self.min_equity_usdt))
        return self


class AiState(BaseModel):
    last_run_at: datetime | None = None
    last_status: str = "never"
    token_budget_usd_month: float = 30.0


class Params(BaseModel):
    version: int = 1
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: UpdatedBy = "system"
    market_mode: MarketMode = "futures"
    symbol_selection: SymbolSelection = "ai_approve"
    strategy_mode: StrategyMode = "trend"
    risk_grade: RiskGrade = "conservative"
    ai_level: AiLevel = "params_only"
    stop_style: StopStyle = "atr"
    run_state: RunState = "running"
    symbols: Symbols = Field(default_factory=Symbols)
    strategy: StrategyParams = Field(default_factory=StrategyParams)
    risk: RiskLimits = Field(default_factory=RiskLimits)
    manual_band: ManualBand = Field(default_factory=ManualBand)
    ai: AiState = Field(default_factory=AiState)

    @model_validator(mode="after")
    def apply_grade_if_default_mismatch(self) -> Self:
        from helm.config.defaults import RISK_PRESETS

        preset = RISK_PRESETS[self.risk_grade]
        if self.updated_by != "ai_batch":
            self.risk.leverage = preset.leverage
            self.risk.max_concurrent_positions = preset.max_concurrent_positions
        return self


class ClampResult(BaseModel):
    params: Params
    warnings: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    cursor = data
    for key in keys[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[keys[-1]] = value


def clamp_params(raw: dict[str, Any] | Params) -> ClampResult:
    payload = raw.model_dump() if isinstance(raw, Params) else dict(raw)
    warnings: list[str] = []
    rejected: list[str] = []

    leverage = payload.get("risk", {}).get("leverage")
    if leverage is not None and not (1 <= int(leverage) <= 3):
        rejected.append("risk.leverage")
        payload.setdefault("risk", {})["leverage"] = 1

    params = Params.model_validate(payload)
    return ClampResult(params=params, warnings=warnings, rejected=rejected)


def merge_ai_patches(current: Params, patches: dict[str, Any]) -> ClampResult:
    data = current.model_dump()
    rejected: list[str] = []
    for path, value in patches.items():
        if path in AI_LOCKED_FIELDS or path.split(".")[0] in AI_LOCKED_FIELDS:
            rejected.append(path)
            continue
        if path not in AI_PATCH_WHITELIST:
            rejected.append(path)
            continue
        _set_path(data, path, value)
    data["updated_by"] = "ai_batch"
    data["updated_at"] = datetime.now(timezone.utc)
    data["version"] = current.version + 1
    result = clamp_params(data)
    result.rejected.extend(rejected)
    return result


def apply_user_patch(current: Params, patch: dict[str, Any]) -> ClampResult:
    data = current.model_dump()
    rejected: list[str] = []
    for path, value in patch.items():
        if path not in USER_PATCH_FIELDS:
            rejected.append(path)
            continue
        _set_path(data, path, value)
    data["updated_by"] = "user"
    data["updated_at"] = datetime.now(timezone.utc)
    data["version"] = current.version + 1
    if "risk_grade" in patch:
        from helm.config.defaults import RISK_PRESETS

        kept_min = data.get("risk", {}).get("min_equity_usdt", 0)
        data["risk"] = RISK_PRESETS[patch["risk_grade"]].model_dump()
        data["risk"]["min_equity_usdt"] = kept_min
    result = clamp_params(data)
    result.rejected.extend(rejected)
    return result
