import { useState } from "react";

export function ManualTrade({
  jobs,
  onCreate,
  onToggle,
  onDelete,
}: {
  jobs: Array<Record<string, unknown>>;
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
      <h2>수동 투자</h2>
      <p className="muted">
        하한 = 손절(더 내려가면 안 됨), 상한 = 익절. AI 키 없이 저장됩니다. 실주문 연결 전엔 의도로만 남습니다.
      </p>
      <form
        className="band-form"
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
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </label>
        <label>
          하한
          <input value={lower} onChange={(e) => setLower(e.target.value)} />
        </label>
        <label>
          상한
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
        <button type="submit">밴드 저장</button>
      </form>
      <ul className="job-list">
        {jobs.map((job) => (
          <li key={String(job.id)}>
            <strong>{String(job.symbol)}</strong> {String(job.lower)} – {String(job.upper)} / {String(job.size_usdt)} USDT
            <span className="muted"> {String(job.schedule)}</span>
            <button type="button" onClick={() => onToggle(Number(job.id), !job.enabled)}>
              {job.enabled ? "끄기" : "켜기"}
            </button>
            <button type="button" className="danger" onClick={() => onDelete(Number(job.id))}>
              삭제
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
