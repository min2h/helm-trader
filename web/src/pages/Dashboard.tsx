import { LoadingBar } from "../LoadingBar";
import { formatInt, formatMoney, formatPct, formatWhen } from "../format";
import {
  AI_LEVEL,
  MARKET_MODE,
  RISK_GRADE,
  RUN_STATE,
  STOP_STYLE,
  STRATEGY_MODE,
  SYMBOL_SELECTION,
  labelOf,
} from "../labels";

const STATE_HELP: Record<string, string> = {
  running: "신규 진입이 허용되어 있습니다. 손절·익절은 거래소 조건이 유지됩니다.",
  soft_stop: "새 매수만 멈춥니다. 이미 연 포지션의 손절·익절은 그대로입니다.",
  hard_kill: "전량 청산 후 정지입니다. 재개하려면 포지션이 비어 있어야 합니다.",
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function Dashboard({
  status,
  params,
  onSoftStop,
  onResume,
  onHardKill,
  onOpenSettings,
  loading = false,
  mark = null,
  usdKrw = 0,
}: {
  status: Record<string, unknown> | null;
  params: Record<string, unknown> | null;
  onSoftStop: () => void | Promise<void>;
  onResume: () => void | Promise<void>;
  onHardKill: () => void | Promise<void>;
  onOpenSettings: () => void;
  loading?: boolean;
  mark?: { symbol: string; price: number | null } | null;
  usdKrw?: number;
}) {
  if (!status) return <LoadingBar show label="상태를 불러오는 중…" />;
  const state = String(status.run_state);
  const risk = asRecord(params?.risk);
  const symbols = Array.isArray(status.active_symbols) ? (status.active_symbols as string[]) : [];
  const last = asRecord(status.last_command);

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">운영 현황</p>
          <h2>한눈에 보기</h2>
        </div>
        <button type="button" className="primary" onClick={onOpenSettings}>
          설정 열기
        </button>
      </div>
      <LoadingBar show={loading} label="최신 상태 확인 중…" />

      <p className="state-banner soft_stop">
        지금 되는 것: 로그인·설정·종목·수동밴드·시세. 오늘 손익·열린 포지션·실주문은 엔진 연결 전이라 0으로 보입니다.
      </p>
      <p className={`state-banner ${state}`}>
        {labelOf(RUN_STATE, state)} — {STATE_HELP[state] ?? state}
      </p>

      <div className="grid-stats">
        <article className="stat">
          <dt>시세 {mark?.symbol || "BTCUSDT"}</dt>
          <dd>{mark?.price == null ? "연결 확인 중" : formatMoney(mark.price, usdKrw, 2)}</dd>
        </article>
        <article className="stat">
          <dt>오늘 손익</dt>
          <dd className={Number(status.daily_pnl_pct) < 0 ? "neg" : "pos"}>
            {formatPct(status.daily_pnl_pct)}
          </dd>
        </article>
        <article className="stat">
          <dt>드로다운</dt>
          <dd className={Number(status.drawdown_from_peak_pct) > 0 ? "neg" : ""}>
            {formatPct(status.drawdown_from_peak_pct || 0)}
          </dd>
        </article>
        <article className="stat">
          <dt>열린 포지션</dt>
          <dd>{formatInt(status.open_positions ?? 0)}</dd>
        </article>
        <article className="stat">
          <dt>MIN 잔고</dt>
          <dd>{formatMoney(status.min_equity_usdt || 0, usdKrw, 0)}</dd>
        </article>
        <article className="stat">
          <dt>AI 배치</dt>
          <dd>{String(status.ai_last_status ?? "never")}</dd>
        </article>
        <article className="stat">
          <dt>하트비트</dt>
          <dd style={{ fontSize: 15 }}>{formatWhen(status.heartbeat_at)}</dd>
        </article>
      </div>

      <div className="page-head">
        <h3>현재 설정</h3>
        <button type="button" onClick={onOpenSettings}>
          수정
        </button>
      </div>
      <div className="grid-stats">
        <article className="stat">
          <dt>시장</dt>
          <dd>{labelOf(MARKET_MODE, status.market_mode ?? params?.market_mode)}</dd>
        </article>
        <article className="stat">
          <dt>전략</dt>
          <dd>{labelOf(STRATEGY_MODE, status.strategy_mode)}</dd>
        </article>
        <article className="stat">
          <dt>리스크</dt>
          <dd>{labelOf(RISK_GRADE, status.risk_grade)}</dd>
        </article>
        <article className="stat">
          <dt>AI</dt>
          <dd>{labelOf(AI_LEVEL, status.ai_level ?? params?.ai_level)}</dd>
        </article>
        <article className="stat">
          <dt>손절</dt>
          <dd>{labelOf(STOP_STYLE, params?.stop_style)}</dd>
        </article>
        <article className="stat">
          <dt>종목 선택</dt>
          <dd>{labelOf(SYMBOL_SELECTION, params?.symbol_selection)}</dd>
        </article>
      </div>

      <div className="page-head">
        <div>
          <h3>적용 중인 리스크 숫자</h3>
          <p className="muted">등급을 바꾸면 서버가 이 값을 다시 채웁니다. 목표 수익률 입력란은 없습니다.</p>
        </div>
      </div>
      <div className="grid-stats">
        <article className="stat">
          <dt>레버리지</dt>
          <dd>{risk.leverage == null ? "—" : `${formatInt(risk.leverage)}x`}</dd>
        </article>
        <article className="stat">
          <dt>회당 리스크</dt>
          <dd>{risk.per_trade_risk_pct == null ? "—" : formatPct(risk.per_trade_risk_pct, 1)}</dd>
        </article>
        <article className="stat">
          <dt>일일 한도</dt>
          <dd>{risk.daily_loss_limit_pct == null ? "—" : formatPct(risk.daily_loss_limit_pct, 1)}</dd>
        </article>
        <article className="stat">
          <dt>MDD 킬</dt>
          <dd>{risk.portfolio_mdd_kill_pct == null ? "—" : formatPct(risk.portfolio_mdd_kill_pct, 1)}</dd>
        </article>
      </div>

      <div className="grid-3" style={{ marginTop: 14 }}>
        <article className="help-card">
          <h3>소프트 정지</h3>
          <p className="muted">새 매수만 멈춥니다. 이미 연 포지션의 손절·익절은 거래소에 남습니다.</p>
          <button type="button" disabled={loading} onClick={() => void onSoftStop()}>
            {loading ? "처리 중…" : "신규 진입 중단"}
          </button>
        </article>
        <article className="help-card">
          <h3>재개</h3>
          <p className="muted">소프트 정지 후 다시 룰대로 진입합니다. 하드 킬 뒤에는 포지션이 비어 있어야 합니다.</p>
          <button type="button" className="primary" disabled={loading} onClick={() => void onResume()}>
            {loading ? "처리 중…" : "다시 가동"}
          </button>
        </article>
        <article className="help-card">
          <h3>전량 청산</h3>
          <p className="muted">두 번 확인합니다. 실주문 연결 전엔 명령만 기록됩니다.</p>
          <button type="button" className="danger" disabled={loading} onClick={() => void onHardKill()}>
            {loading ? "처리 중…" : "전량 청산 (2단계)"}
          </button>
        </article>
      </div>

      <article className="card" style={{ marginTop: 14 }}>
        <h3>활성 종목</h3>
        <div className="chip-list">
          {symbols.length === 0 ? <span className="muted">없음</span> : null}
          {symbols.map((symbol) => (
            <span className="chip" key={symbol}>
              {symbol}
            </span>
          ))}
        </div>
        {last.kind ? (
          <p className="muted" style={{ marginTop: 12 }}>
            마지막 명령: {String(last.kind)} · {String(last.reason ?? "")} · {formatWhen(last.at)}
          </p>
        ) : null}
      </article>
    </section>
  );
}
