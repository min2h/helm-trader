import { useEffect, useMemo, useState } from "react";
import { LoadingBar } from "../LoadingBar";
import { NumberField } from "../NumberField";
import { SymbolSearch, type CatalogItem } from "../SymbolSearch";
import { formatDecimal, formatMoney, parseAmount } from "../format";
import { pickDefaultSymbol } from "../pickSymbol";
import { SCHEDULE, labelOf } from "../labels";

export function ManualTrade({
  jobs,
  catalog,
  compact = false,
  usdKrw = 0,
  onCreate,
  onToggle,
  onDelete,
}: {
  jobs: Array<Record<string, unknown>>;
  catalog: CatalogItem[];
  compact?: boolean;
  usdKrw?: number;
  onCreate: (body: Record<string, unknown>) => Promise<void>;
  onToggle: (id: number, enabled: boolean) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [symbol, setSymbol] = useState("");
  const [lower, setLower] = useState("60000");
  const [upper, setUpper] = useState("75000");
  const [size, setSize] = useState("100");
  const [schedule, setSchedule] = useState("every_15m");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const lowerN = parseAmount(lower);
  const upperN = parseAmount(upper);
  const sizeN = parseAmount(size);
  useEffect(() => {
    if (!symbol && catalog.length) {
      const next = pickDefaultSymbol(catalog);
      if (next) setSymbol(next);
    }
  }, [catalog, symbol]);

  const errors = useMemo(() => {
    const out: string[] = [];
    if (!symbol.trim()) out.push("종목을 고르세요.");
    if (lowerN === null || lowerN <= 0) out.push("하한은 0보다 큰 숫자여야 합니다.");
    if (upperN === null || upperN <= 0) out.push("상한은 0보다 큰 숫자여야 합니다.");
    if (lowerN !== null && upperN !== null && lowerN >= upperN) out.push("하한은 상한보다 작아야 합니다.");
    if (sizeN === null || sizeN < 10) out.push("금액은 $10 이상이어야 합니다.");
    return out;
  }, [symbol, lowerN, upperN, sizeN]);

  return (
    <section>
      {compact ? (
        <h3>수동 투자</h3>
      ) : (
        <div className="page-head">
          <div>
            <p className="eyebrow">밴드</p>
            <h2>수동 투자</h2>
          </div>
        </div>
      )}
      <p className="muted">하한 = 손절, 상한 = 익절. AI 키 없이 저장됩니다. 실주문 연결 전엔 의도로만 남습니다.</p>
      <LoadingBar show={busy} label="저장하는 중…" />

      <form
        className="card form-grid"
        onSubmit={async (event) => {
          event.preventDefault();
          if (errors.length || lowerN === null || upperN === null || sizeN === null) {
            setMessage(errors[0] || "입력을 확인하세요.");
            return;
          }
          setBusy(true);
          setMessage("");
          try {
            await onCreate({
              symbol,
              lower: lowerN,
              upper: upperN,
              size_usdt: sizeN,
              schedule,
              side: "BUY",
            });
            setMessage("밴드를 저장했습니다.");
          } catch (err) {
            setMessage(err instanceof Error ? err.message : "저장에 실패했습니다.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          종목
          <SymbolSearch value={symbol} onChange={setSymbol} catalog={catalog} />
        </label>
        <label>
          하한 (손절)
          <NumberField value={lower} onChange={setLower} decimals={2} min={0} placeholder="60,000.00" />
        </label>
        <label>
          상한 (익절)
          <NumberField value={upper} onChange={setUpper} decimals={2} min={0} placeholder="75,000.00" />
        </label>
        <label>
          금액 ($)
          <NumberField value={size} onChange={setSize} decimals={0} min={10} placeholder="$100" />
        </label>
        <label>
          스케줄
          <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
            <option value="every_15m">15분마다</option>
            <option value="every_1h">1시간마다</option>
            <option value="daily_0800">매일 08:00</option>
          </select>
        </label>
        <button type="submit" className="primary" disabled={busy || errors.length > 0}>
          {busy ? "저장 중…" : "밴드 저장"}
        </button>
      </form>
      {errors.length ? <p className="field-error">{errors[0]}</p> : message ? <p className="muted">{message}</p> : null}

      <div className="grid-3" style={{ marginTop: 14 }}>
        {jobs.length === 0 ? <p className="muted">저장된 밴드가 없습니다.</p> : null}
        {jobs.map((job) => (
          <article className="job-card" key={String(job.id)}>
            <header>
              <strong>{String(job.symbol)}</strong>
              <span className="actions">
                {job.source === "ai" ? <span className="badge">AI</span> : null}
                <span className={`badge ${job.enabled ? "good" : "warn"}`}>{job.enabled ? "켜짐" : "꺼짐"}</span>
              </span>
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
                <dt>스케줄</dt>
                <dd>{labelOf(SCHEDULE, job.schedule)}</dd>
              </div>
            </div>
            <div className="actions">
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await onToggle(Number(job.id), !job.enabled);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {job.enabled ? "끄기" : "켜기"}
              </button>
              <button
                type="button"
                className="danger"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await onDelete(Number(job.id));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                삭제
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
