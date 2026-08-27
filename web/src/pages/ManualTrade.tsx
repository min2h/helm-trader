import { useState } from "react";
import { SymbolSearch, type CatalogItem } from "../SymbolSearch";
import { SCHEDULE, labelOf } from "../labels";

export function ManualTrade({
  jobs,
  catalog,
  compact = false,
  onCreate,
  onToggle,
  onDelete,
}: {
  jobs: Array<Record<string, unknown>>;
  catalog: CatalogItem[];
  compact?: boolean;
  onCreate: (body: Record<string, unknown>) => Promise<void>;
  onToggle: (id: number, enabled: boolean) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [lower, setLower] = useState("60000");
  const [upper, setUpper] = useState("75000");
  const [size, setSize] = useState("100");
  const [schedule, setSchedule] = useState("every_15m");

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

      <form
        className="card form-grid"
        onSubmit={async (event) => {
          event.preventDefault();
          await onCreate({
            symbol,
            lower: Number(lower),
            upper: Number(upper),
            size_usdt: Number(size),
            schedule,
            side: "BUY",
          });
        }}
      >
        <label>
          종목
          <SymbolSearch value={symbol} onChange={setSymbol} catalog={catalog} />
        </label>
        <label>
          하한 (손절)
          <input value={lower} onChange={(e) => setLower(e.target.value)} />
        </label>
        <label>
          상한 (익절)
          <input value={upper} onChange={(e) => setUpper(e.target.value)} />
        </label>
        <label>
          금액 USDT
          <input value={size} onChange={(e) => setSize(e.target.value)} />
        </label>
        <label>
          스케줄
          <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
            <option value="every_15m">15분마다</option>
            <option value="every_1h">1시간마다</option>
            <option value="daily_0800">매일 08:00</option>
          </select>
        </label>
        <button type="submit" className="primary">
          밴드 저장
        </button>
      </form>

      <div className="grid-3" style={{ marginTop: 14 }}>
        {jobs.length === 0 ? <p className="muted">저장된 밴드가 없습니다.</p> : null}
        {jobs.map((job) => (
          <article className="job-card" key={String(job.id)}>
            <header>
              <strong>{String(job.symbol)}</strong>
              <span className={`badge ${job.enabled ? "good" : "warn"}`}>{job.enabled ? "켜짐" : "꺼짐"}</span>
            </header>
            <div className="job-meta">
              <div>
                <dt>하한</dt>
                <dd>{String(job.lower)}</dd>
              </div>
              <div>
                <dt>상한</dt>
                <dd>{String(job.upper)}</dd>
              </div>
              <div>
                <dt>금액</dt>
                <dd>{String(job.size_usdt)} USDT</dd>
              </div>
              <div>
                <dt>스케줄</dt>
                <dd>{labelOf(SCHEDULE, job.schedule)}</dd>
              </div>
            </div>
            <div className="actions">
              <button type="button" onClick={() => onToggle(Number(job.id), !job.enabled)}>
                {job.enabled ? "끄기" : "켜기"}
              </button>
              <button type="button" className="danger" onClick={() => onDelete(Number(job.id))}>
                삭제
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
