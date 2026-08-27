"""AI autopilot: the model ranks symbols, the server computes every number.

Money is on the line, so nothing the model invents is trusted. It may only pick
symbols out of a candidate table built from Binance 24h tickers plus klines, and
pick a schedule out of a fixed enum. Entry bands, stops and order size come from
ATR on real bars and from the user's own risk params.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, Field

from helm.ai.client import try_parse_json_block
from helm.ai.news import fetch_headlines
from helm.ai.prompt import AUTOPILOT_TASK
from helm.ai.screener import fetch_usdt_tickers, screen_symbols
from helm.config.schema import Params
from helm.research.data import fetch_klines
from helm.research.http import first_json
from helm.strategies.signals import adx, atr

SCHEDULES = ("every_15m", "every_1h", "daily_0800")
TIMEFRAME_SCHEDULE = {
    "1m": "every_15m",
    "5m": "every_15m",
    "15m": "every_15m",
    "1h": "every_1h",
    "4h": "daily_0800",
    "1d": "daily_0800",
}
MIN_QUOTE_VOLUME = 20_000_000.0
ATR_PCT_RANGE = (0.15, 15.0)
MIN_CONFIDENCE = 0.55
RULE_MIN_SCORE = 0.30
TAKE_R = 2.0
FUNDING_URLS = ["https://fapi.binance.com/fapi/v1/premiumIndex"]


@dataclass(frozen=True)
class Evidence:
    """Verified per-symbol facts. Every field comes from an exchange response."""

    symbol: str
    last: float
    change_pct: float
    quote_volume: float
    atr: float
    atr_pct: float
    adx: float
    range_high: float
    range_low: float
    funding_apr: float | None
    bars: int
    timeframe: str

    def as_row(self) -> str:
        funding = "데이터 없음" if self.funding_apr is None else f"{self.funding_apr:.2f}%"
        return (
            f"| {self.symbol} | {self.last:,.6g} | {self.change_pct:+.2f}% | "
            f"{self.quote_volume/1_000_000:,.0f}M | {self.atr:,.6g} | {self.atr_pct:.2f}% | "
            f"{self.adx:.1f} | {self.range_high:,.6g} | {self.range_low:,.6g} | {funding} |"
        )


@dataclass
class EvidencePack:
    timeframe: str
    market: str
    candidates: list[Evidence] = field(default_factory=list)
    headlines: list[dict] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def by_symbol(self) -> dict[str, Evidence]:
        return {item.symbol: item for item in self.candidates}


class Pick(BaseModel):
    symbol: str = ""
    schedule: str = ""
    confidence: float = 0.0
    reason: str = ""


class RawPlan(BaseModel):
    regime: str = ""
    picks: list[Pick] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@dataclass
class PlannedJob:
    symbol: str
    schedule: str
    lower: float
    upper: float
    size_usdt: float
    confidence: float
    reason: str
    evidence: Evidence


def _funding_apr_map(market: str) -> dict[str, float]:
    if market == "spot":
        return {}
    try:
        rows = first_json(FUNDING_URLS, timeout=12)
    except Exception:
        return {}
    out: dict[str, float] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        try:
            rate = float(row.get("lastFundingRate"))
        except (TypeError, ValueError):
            continue
        out[str(row.get("symbol", "")).upper()] = rate * 3 * 365 * 100
    return out


def _stats(frame: pd.DataFrame, *, atr_n: int, donchian_n: int) -> tuple[float, float, float, float, float] | None:
    if frame.empty or len(frame) < max(atr_n, donchian_n) + 5:
        return None
    atr_value = float(atr(frame["high"], frame["low"], frame["close"], atr_n).iloc[-1])
    adx_raw = float(adx(frame["high"], frame["low"], frame["close"], atr_n).iloc[-1])
    last = float(frame["close"].iloc[-1])
    if not math.isfinite(atr_value) or atr_value <= 0 or last <= 0:
        return None
    high = float(frame["high"].tail(donchian_n).max())
    low = float(frame["low"].tail(donchian_n).min())
    adx_value = adx_raw if math.isfinite(adx_raw) else 0.0
    return last, atr_value, adx_value, high, low


def collect_evidence(
    params: Params,
    *,
    exclude: list[str] | None = None,
    scan: int = 8,
) -> EvidencePack:
    """Build the candidate table. Network heavy but bounded: 2 + scan requests."""
    market = "spot" if params.market_mode == "spot" else "futures"
    timeframe = params.strategy.trend.timeframe or "15m"
    atr_n = params.strategy.trend.atr_n
    donchian_n = params.strategy.trend.donchian_n
    skip = {s.upper() for s in (exclude or [])}
    pack = EvidencePack(timeframe=timeframe, market=market, excluded=sorted(skip))

    tickers = fetch_usdt_tickers(market)
    ranked = screen_symbols(tickers, blacklist=params.symbols.blacklist, top_n=60)
    volumes = {str(row.get("symbol", "")).upper(): row for row in tickers if isinstance(row, dict)}
    funding = _funding_apr_map(market)

    for symbol in ranked:
        if len(pack.candidates) >= scan:
            break
        if symbol in skip:
            continue
        row = volumes.get(symbol, {})
        quote_volume = float(row.get("quoteVolume") or 0)
        if quote_volume < MIN_QUOTE_VOLUME:
            continue
        try:
            frame = fetch_klines(symbol, timeframe, limit=240, market=market, timeout=15)
        except Exception as exc:
            pack.notes.append(f"{symbol} 시세 조회 실패: {exc}")
            continue
        stats = _stats(frame, atr_n=atr_n, donchian_n=donchian_n)
        if not stats:
            pack.notes.append(f"{symbol} 지표 계산 불가(봉 부족)")
            continue
        last, atr_value, adx_value, high, low = stats
        atr_pct = atr_value / last * 100
        if not ATR_PCT_RANGE[0] <= atr_pct <= ATR_PCT_RANGE[1]:
            pack.notes.append(f"{symbol} 변동성 범위 밖 (ATR {atr_pct:.2f}%)")
            continue
        pack.candidates.append(
            Evidence(
                symbol=symbol,
                last=last,
                change_pct=float(row.get("priceChangePercent") or 0),
                quote_volume=quote_volume,
                atr=atr_value,
                atr_pct=atr_pct,
                adx=adx_value,
                range_high=high,
                range_low=low,
                funding_apr=funding.get(symbol),
                bars=len(frame),
                timeframe=timeframe,
            )
        )
    pack.headlines = fetch_headlines(limit=12)
    return pack


def max_picks(params: Params) -> int:
    return max(1, min(3, params.risk.max_concurrent_positions))


def build_autopilot_prompt(params: Params, pack: EvidencePack, *, picks: int) -> str:
    table = "\n".join(item.as_row() for item in pack.candidates) or "| (후보 없음) |"
    news = "\n".join(f"- {item['title']}" for item in pack.headlines) or "- (뉴스 피드 없음)"
    avoided = ", ".join(pack.excluded) or "없음"
    return (
        f"{AUTOPILOT_TASK}\n"
        f"고를 수 있는 종목 수: 최대 {picks}개\n"
        f"직전 분석에서 이미 돌린 종목(이번엔 제외됨): {avoided}\n"
        f"기준 봉: {pack.timeframe} / 시장: {pack.market} / "
        f"손절 ATR배수: {params.strategy.trend.atr_stop_mult} / "
        f"레버리지 상한: {params.risk.leverage}x / "
        f"회당 리스크: {params.risk.per_trade_risk_pct}% / "
        f"일일 손실 한도: {params.risk.daily_loss_limit_pct}%\n"
        f"현재 전략: {params.strategy_mode} / 등급: {params.risk_grade} / "
        f"운전 상태: {params.run_state}\n\n"
        "[검증된 후보 표 — 이 안에서만 고른다]\n"
        "| 심볼 | 최근가 | 24h변동 | 24h거래대금 | ATR | ATR% | ADX | 최근고가 | 최근저가 | 펀딩APR |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        f"{table}\n\n"
        f"[헤드라인]\n{news}\n\n"
        f"[수집 경고]\n" + ("\n".join(f"- {n}" for n in pack.notes) or "- 없음") + "\n"
    )


def validate_plan(
    reply: str,
    pack: EvidencePack,
    *,
    limit: int,
    min_confidence: float = MIN_CONFIDENCE,
) -> tuple[RawPlan, list[tuple[Pick, Evidence]], list[str]]:
    """Drop anything the model made up. Only table symbols and enum schedules survive."""
    payload = try_parse_json_block(reply)
    rejected: list[str] = []
    if not payload:
        return RawPlan(), [], ["AI 응답에서 JSON을 찾지 못해 실행하지 않았습니다."]
    plan = RawPlan.model_validate(payload)
    known = pack.by_symbol()
    default_schedule = TIMEFRAME_SCHEDULE.get(pack.timeframe, "every_1h")
    accepted: list[tuple[Pick, Evidence]] = []
    seen: set[str] = set()
    for pick in plan.picks:
        symbol = pick.symbol.strip().upper()
        evidence = known.get(symbol)
        if not symbol:
            rejected.append("심볼 없는 추천 제외")
            continue
        if evidence is None:
            rejected.append(f"{symbol}: 검증 표에 없는 종목이라 제외")
            continue
        if symbol in seen:
            rejected.append(f"{symbol}: 중복 추천 제외")
            continue
        if pick.confidence < min_confidence:
            rejected.append(f"{symbol}: 확신도 {pick.confidence:.2f} < {min_confidence} 제외")
            continue
        if len(pick.reason.strip()) < 8:
            rejected.append(f"{symbol}: 근거 문장이 없어 제외")
            continue
        schedule = pick.schedule.strip()
        if schedule not in SCHEDULES:
            rejected.append(f"{symbol}: 스케줄 '{schedule}' 대신 {default_schedule} 적용")
            schedule = default_schedule
        seen.add(symbol)
        accepted.append((pick.model_copy(update={"symbol": symbol, "schedule": schedule}), evidence))
        if len(accepted) >= limit:
            break
    if len(plan.picks) > limit:
        rejected.append(f"추천 {len(plan.picks)}개 중 동시 포지션 한도 {limit}개까지만 실행")
    return plan, accepted, rejected


def rule_regime(pack: EvidencePack) -> str:
    if not pack.candidates:
        return "range"
    average = sum(item.adx for item in pack.candidates) / len(pack.candidates)
    if average >= 25:
        return "trend"
    if average <= 15:
        return "range"
    return "high_vol_chop"


def rule_rank(
    params: Params,
    pack: EvidencePack,
    *,
    limit: int,
) -> tuple[list[tuple[Pick, Evidence]], list[str]]:
    """Symbol choice with no LLM at all. Same verified table, deterministic score."""
    mode = params.strategy_mode
    schedule = TIMEFRAME_SCHEDULE.get(pack.timeframe, "every_1h")
    scored: list[tuple[float, str, Evidence]] = []
    for item in pack.candidates:
        volume_score = min(item.quote_volume / 1_000_000_000, 1.0)
        if mode == "grid":
            width_pct = (item.range_high - item.range_low) / item.last * 100
            shape = max(0.0, 1.0 - item.adx / 40)
            fit = min(width_pct / 5, 1.0)
            reason = (
                f"규칙 선정: ADX {item.adx:.1f}로 횡보, 밴드폭 {width_pct:.2f}%, "
                f"거래대금 {item.quote_volume/1_000_000:,.0f}M USDT"
            )
        elif mode == "funding_arb":
            apr = item.funding_apr or 0.0
            shape = min(max(apr / 30, 0.0), 1.0)
            fit = min(item.atr_pct / 3, 1.0)
            funding_text = "데이터 없음" if item.funding_apr is None else f"{apr:.1f}% APR"
            reason = (
                f"규칙 선정: 펀딩 {funding_text}, ATR {item.atr_pct:.2f}%, "
                f"거래대금 {item.quote_volume/1_000_000:,.0f}M USDT"
            )
        else:
            shape = min(item.adx / 40, 1.0)
            fit = min(item.atr_pct / 3, 1.0)
            reason = (
                f"규칙 선정: ADX {item.adx:.1f} 추세, ATR {item.atr_pct:.2f}%, "
                f"거래대금 {item.quote_volume/1_000_000:,.0f}M USDT"
            )
        scored.append((shape * 0.5 + volume_score * 0.3 + fit * 0.2, reason, item))

    scored.sort(key=lambda row: (-row[0], row[2].symbol))
    accepted: list[tuple[Pick, Evidence]] = []
    rejected: list[str] = []
    for score, reason, item in scored:
        if len(accepted) >= limit:
            rejected.append(f"{item.symbol}: 동시 포지션 한도 {limit}개를 넘어 제외")
            continue
        if score < RULE_MIN_SCORE:
            rejected.append(f"{item.symbol}: 규칙 점수 {score:.2f} < {RULE_MIN_SCORE} 제외")
            continue
        accepted.append(
            (
                Pick(symbol=item.symbol, schedule=schedule, confidence=round(score, 2), reason=reason),
                item,
            )
        )
    return accepted, rejected


def _round_price(value: float) -> float:
    if value >= 1000:
        return round(value, 2)
    if value >= 1:
        return round(value, 4)
    return round(value, 6)


def plan_jobs(params: Params, accepted: list[tuple[Pick, Evidence]]) -> list[PlannedJob]:
    """Bands come from ATR on real bars; size comes from the user's own setting."""
    stop_mult = params.strategy.trend.atr_stop_mult
    size = params.manual_band.size_usdt
    jobs: list[PlannedJob] = []
    for pick, evidence in accepted:
        lower = evidence.last - evidence.atr * stop_mult
        upper = evidence.last + evidence.atr * stop_mult * TAKE_R
        if lower <= 0:
            lower = evidence.last * 0.5
        if upper <= lower:
            continue
        jobs.append(
            PlannedJob(
                symbol=evidence.symbol,
                schedule=pick.schedule,
                lower=_round_price(lower),
                upper=_round_price(upper),
                size_usdt=size,
                confidence=round(pick.confidence, 2),
                reason=pick.reason.strip(),
                evidence=evidence,
            )
        )
    return jobs


def render_plan_markdown(
    params: Params,
    pack: EvidencePack,
    plan: RawPlan,
    jobs: list[PlannedJob],
    rejected: list[str],
    *,
    engine: str = "ai",
) -> str:
    picker = "AI(LLM)" if engine == "ai" else "규칙 엔진 (LLM 토큰 0)"
    lines = [
        "# 자동매매 계획",
        "",
        f"- 종목 선정: {picker}",
        f"- 레짐 판단: {plan.regime or '미기재'}",
        f"- 기준 봉: {pack.timeframe} / 시장: {pack.market}",
        f"- 후보 {len(pack.candidates)}개 중 {len(jobs)}개 실행",
        f"- 회당 금액: {params.manual_band.size_usdt:,.0f} USDT (설정값)",
        f"- 손절 폭: ATR x {params.strategy.trend.atr_stop_mult}, 목표 {TAKE_R}R (서버 계산)",
        "",
        "## 실행 종목",
    ]
    if not jobs:
        lines.append("- 검증을 통과한 종목이 없어 실행하지 않았습니다.")
    for job in jobs:
        ev = job.evidence
        lines += [
            f"### {job.symbol} ({job.schedule}, 확신 {job.confidence})",
            f"- 밴드: {job.lower:,.6g} ~ {job.upper:,.6g} (최근가 {ev.last:,.6g})",
            f"- 근거 지표: ATR {ev.atr_pct:.2f}%, ADX {ev.adx:.1f}, "
            f"24h {ev.change_pct:+.2f}%, 거래대금 {ev.quote_volume/1_000_000:,.0f}M USDT",
            f"- 선정 사유: {job.reason}",
        ]
    lines += ["", "## 검증에서 걸러진 것"]
    lines += [f"- {item}" for item in rejected] or ["- 없음"]
    lines += ["", "## 경고"]
    lines += [f"- {item}" for item in plan.warnings] or ["- 없음"]
    lines += ["", "## 참고 헤드라인"]
    lines += [f"- {item['title']}" for item in pack.headlines[:8]] or ["- 없음"]
    lines += [
        "",
        "> 가격·손절·금액은 선정 주체가 정하지 않습니다. 종목과 주기만 고르고,",
        "> 숫자는 거래소 봉 데이터와 사용자 리스크 설정으로 서버가 계산합니다.",
    ]
    return "\n".join(lines)
