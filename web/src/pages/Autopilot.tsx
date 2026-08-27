import { useState } from "react";
import { api, type AutopilotRun, type AutopilotState } from "../api";
import { LoadingBar } from "../LoadingBar";
import { formatDecimal, formatMoney } from "../format";
import { SCHEDULE, labelOf } from "../labels";

export function Autopilot({
  state,
  usdKrw,
  onChanged,
  onReport,
  onSettings,
}: {
  state: AutopilotState | null;
  usdKrw: number;
  onChanged: () => Promise<void>;
  onReport: (markdown: string) => void;
  onSettings: () => void;
}) {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [last, setLast] = useState<AutopilotRun | null>(null);

  const running = (state?.enabled_count ?? 0) > 0;
  const blocked = !state?.has_binance;
  const byAi = state?.engine === "ai";

  async function call(label: string, fn: () => Promise<string>) {
    setBusy(label);
    setMessage("");
    setFailed(false);
    try {
      setMessage(await fn());
    } catch (err) {
      setFailed(true);
      setMessage(err instanceof Error ? err.message.replace(/^\d+\s*/, "") : "요청에 실패했습니다.");
    } finally {
      setBusy("");
      await onChanged();
    }
  }

  async function run(again: boolean) {
    await call(again ? "재분석" : "분석", async () => {
      const result = await api.runAutopilot(again);
      setLast(result);
      if (result.markdown) onReport(result.markdown);
      const picker = result.engine === "ai" ? "AI가" : "규칙 엔진이";
      if (!result.started) return result.reason || "검증을 통과한 종목이 없어 실행하지 않았습니다.";
      const resumed = result.resumed === false ? " (엔진 재개는 직접 눌러야 합니다)" : "";
      return `${picker} 고른 ${result.symbols?.join(", ")} 자동매매를 시작했습니다.${resumed}`;
    });
  }

  return (
    <section className="card stack-fields">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h3>자동매매</h3>
          <p className="muted">
            거래대금·ATR·ADX·펀딩·뉴스를 먼저 수집하고, 그 검증된 표 안에서 종목과 주기만 고릅니다. 가격과 금액은
            서버가 계산합니다.
          </p>
        </div>
        <span className="actions">
          <span className="badge">{byAi ? "AI 선정" : "규칙 선정 · 토큰 0"}</span>
          <span className={`badge ${running ? "good" : "warn"}`}>{running ? "실행 중" : "대기"}</span>
        </span>
      </div>
      <LoadingBar
        show={!!busy}
        label={busy === "재분석" ? "다른 종목을 찾는 중…" : busy === "분석" ? "심층분석 중…" : "중지하는 중…"}
      />

      {blocked ? (
        <p className="state-banner soft_stop">
          Binance API 키와 시크릿만 넣으면 바로 실행됩니다. LLM 키는 없어도 됩니다.{" "}
          <button type="button" className="link" onClick={onSettings}>
            설정으로 가기
          </button>
        </p>
      ) : (
        <>
          <div className="actions">
            <button type="button" className="primary" disabled={!!busy} onClick={() => void run(false)}>
              {busy === "분석" ? "분석 중…" : "심층분석 후 자동매매 실행"}
            </button>
            <button type="button" disabled={!!busy} onClick={() => void run(true)}>
              {busy === "재분석" ? "재분석 중…" : "재분석 (다른 종목)"}
            </button>
            <button
              type="button"
              className="danger"
              disabled={!!busy || !running}
              onClick={() =>
                void call("중지", async () => {
                  const result = await api.stopAutopilot();
                  return `자동매매 ${result.stopped_jobs}건을 끄고 신규 진입을 막았습니다. 보유분 청산은 현황 탭의 전량 청산을 쓰세요.`;
                })
              }
            >
              중지
            </button>
          </div>
          <p className="muted">
            회당 금액 {formatMoney(state?.size_usdt ?? 0, usdKrw, 0)} · 동시 최대 {state?.max_picks ?? 1}종목 · 마지막 상태{" "}
            {state?.last_status || "없음"}
          </p>
          <p className="muted">
            {byAi
              ? "AI가 검증 표 안에서 종목과 주기를 고릅니다."
              : "LLM 없이 거래대금·ADX·ATR 점수로 고릅니다. 토큰을 쓰지 않습니다. 설정에서 AI 개입을 “파라미터 + 종목 추천”으로 바꾸고 LLM 키를 넣으면 AI가 고릅니다."}
          </p>
          <p className="muted">
            실행하면 활성 종목이 추천 종목으로 교체되고, 재분석하면 직전 3회에 돌린 종목은 후보에서 빠집니다. 중지는
            신규 진입만 막습니다. 보유분까지 팔려면 현황 탭의 전량 청산을 쓰세요.
          </p>
        </>
      )}

      {message ? <p className={failed ? "field-error" : "muted"}>{message}</p> : null}

      {state?.jobs.length ? (
        <div className="stack-fields">
          {state.jobs.map((job) => (
            <article className="job-card" key={job.id}>
              <header>
                <strong>{job.symbol}</strong>
                <span className={`badge ${job.enabled ? "good" : "warn"}`}>{job.enabled ? "켜짐" : "꺼짐"}</span>
              </header>
              <div className="job-meta">
                <div>
                  <dt>하한</dt>
                  <dd>{formatDecimal(job.lower, 2)}</dd>
                </div>
                <div>
                  <dt>상한</dt>
                  <dd>{formatDecimal(job.upper, 2)}</dd>
                </div>
                <div>
                  <dt>금액</dt>
                  <dd>{formatMoney(job.size_usdt, usdKrw, 0)}</dd>
                </div>
                <div>
                  <dt>주기</dt>
                  <dd>{labelOf(SCHEDULE, job.schedule)}</dd>
                </div>
              </div>
              {job.note ? <p className="muted">{job.note}</p> : null}
            </article>
          ))}
        </div>
      ) : null}

      {last && (last.rejected.length || last.warnings.length) ? (
        <details className="card">
          <summary>검증에서 걸러진 것 / AI 경고</summary>
          <ul className="muted">
            {last.rejected.map((item) => (
              <li key={`r-${item}`}>{item}</li>
            ))}
            {last.warnings.map((item) => (
              <li key={`w-${item}`}>{item}</li>
            ))}
          </ul>
        </details>
      ) : null}

      {state?.history.length ? (
        <p className="muted">
          최근 분석: {state.history.map((run) => run.symbols.join("/") || "선택 없음").join(" → ")}
        </p>
      ) : null}
    </section>
  );
}
