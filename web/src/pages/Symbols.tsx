import { useState } from "react";
import { LoadingBar } from "../LoadingBar";
import { formatInt } from "../format";
import { SymbolSearch, type CatalogItem } from "../SymbolSearch";

export function Symbols({
  symbols,
  catalog,
  onApprove,
  onAddActive,
  onRemoveActive,
}: {
  symbols: { active: string[]; pending_approval: string[]; blacklist: string[] } | null;
  catalog: CatalogItem[];
  onApprove: (symbol: string) => void | Promise<void>;
  onAddActive: (symbol: string) => Promise<void>;
  onRemoveActive: (symbol: string) => Promise<void>;
}) {
  const [pick, setPick] = useState("BTCUSDT");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);

  if (!symbols) return <LoadingBar show label="종목 목록을 불러오는 중…" />;

  const known = catalog.length === 0 || catalog.some((item) => item.symbol === pick);
  const already = symbols.active.includes(pick);

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">유니버스</p>
          <h2>종목</h2>
          <p className="muted">코드를 외울 필요 없습니다. 검색해서 고르면 됩니다. 승인 전에는 엔진이 새 심볼을 구독하지 않습니다.</p>
        </div>
      </div>
      <LoadingBar show={Boolean(busy)} label={busy} />
      <form
        className="card toolbar"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!pick.trim()) {
            setFailed(true);
            setMessage("종목을 고르세요.");
            return;
          }
          if (!known) {
            setFailed(true);
            setMessage("목록에 있는 종목을 고르세요.");
            return;
          }
          if (already) {
            setFailed(true);
            setMessage("이미 가동 목록에 있습니다.");
            return;
          }
          setBusy("종목 추가 중…");
          setFailed(false);
          setMessage("");
          try {
            await onAddActive(pick);
            setMessage(`${pick}을(를) 추가했습니다.`);
          } catch (err) {
            setFailed(true);
            setMessage(err instanceof Error ? err.message : "추가에 실패했습니다.");
          } finally {
            setBusy("");
          }
        }}
      >
        <label>
          가동 목록에 추가
          <SymbolSearch value={pick} onChange={setPick} catalog={catalog} />
        </label>
        <button type="submit" className="primary" disabled={Boolean(busy) || !pick.trim() || already}>
          {busy.startsWith("종목 추가") ? "추가 중…" : "추가"}
        </button>
      </form>
      {message ? <p className={failed ? "field-error" : "muted"}>{message}</p> : null}
      <div className="grid-3" style={{ marginTop: 14 }}>
        <article className="card">
          <h3>가동 중 · {formatInt(symbols.active.length)}</h3>
          <div className="chip-list">
            {symbols.active.length === 0 ? <span className="muted">없음</span> : null}
            {symbols.active.map((symbol) => (
              <span className="chip" key={symbol}>
                {symbol}
                <button
                  type="button"
                  className="danger"
                  disabled={Boolean(busy)}
                  onClick={() => {
                    setBusy("종목 제거 중…");
                    void Promise.resolve(onRemoveActive(symbol)).finally(() => setBusy(""));
                  }}
                >
                  빼기
                </button>
              </span>
            ))}
          </div>
        </article>
        <article className="card">
          <h3>승인 대기 · {formatInt(symbols.pending_approval.length)}</h3>
          <div className="chip-list">
            {symbols.pending_approval.length === 0 ? <span className="muted">대기 없음</span> : null}
            {symbols.pending_approval.map((symbol) => (
              <span className="chip" key={symbol}>
                {symbol}
                <button
                  type="button"
                  className="primary"
                  disabled={Boolean(busy)}
                  onClick={() => {
                    setBusy("승인 중…");
                    void Promise.resolve(onApprove(symbol)).finally(() => setBusy(""));
                  }}
                >
                  승인
                </button>
              </span>
            ))}
          </div>
        </article>
        <article className="card">
          <h3>블랙리스트 · {formatInt(symbols.blacklist.length)}</h3>
          <div className="chip-list">
            {symbols.blacklist.length === 0 ? <span className="muted">없음</span> : null}
            {symbols.blacklist.map((symbol) => (
              <span className="chip" key={symbol}>
                {symbol}
              </span>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
