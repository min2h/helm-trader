const STATE_LABEL: Record<string, string> = {
  running: "가동 중 — 신규 진입 허용",
  soft_stop: "소프트 정지 — 신규 진입만 중단, 손절은 유지",
  hard_kill: "하드 킬 — 전량 청산 후 정지",
};

export function Dashboard({
  status,
  onSoftStop,
  onResume,
  onHardKill,
}: {
  status: Record<string, unknown> | null;
  onSoftStop: () => void;
  onResume: () => void;
  onHardKill: () => void;
}) {
  if (!status) return <p>상태 로딩…</p>;
  const state = String(status.run_state);
  return (
    <section>
      <h2>한눈에 보기</h2>
      <p className={`state-banner ${state}`}>{STATE_LABEL[state] ?? state}</p>
      <dl className="stats">
        <div>
          <dt>오늘 손익</dt>
          <dd className={Number(status.daily_pnl_pct) < 0 ? "neg" : "pos"}>
            {Number(status.daily_pnl_pct).toFixed(2)}%
          </dd>
        </div>
        <div>
          <dt>열린 포지션</dt>
          <dd>{String(status.open_positions)}</dd>
        </div>
        <div>
          <dt>전략</dt>
          <dd>{String(status.strategy_mode)}</dd>
        </div>
        <div>
          <dt>리스크 등급</dt>
          <dd>{String(status.risk_grade)}</dd>
        </div>
        <div>
          <dt>AI 배치</dt>
          <dd>{String(status.ai_last_status)}</dd>
        </div>
        <div>
          <dt>하트비트</dt>
          <dd>{String(status.heartbeat_at ?? "아직 없음")}</dd>
        </div>
      </dl>
      <div className="help-grid">
        <article>
          <h3>소프트 정지</h3>
          <p>새 매수만 멈춥니다. 이미 연 포지션의 손절·익절은 거래소에 남습니다.</p>
        </article>
        <article>
          <h3>재개</h3>
          <p>소프트 정지 후 다시 룰대로 진입합니다. 하드 킬 뒤에는 포지션이 비어 있어야 합니다.</p>
        </article>
        <article>
          <h3>전량 청산</h3>
          <p>두 번 확인합니다. 모든 포지션을 시장가로 닫습니다. 실주문 연결 전엔 명령만 기록됩니다.</p>
        </article>
      </div>
      <div className="actions">
        <button type="button" onClick={onSoftStop}>
          신규 진입 중단
        </button>
        <button type="button" onClick={onResume}>
          다시 가동
        </button>
        <button type="button" className="danger" onClick={onHardKill}>
          전량 청산 (2단계)
        </button>
      </div>
    </section>
  );
}
