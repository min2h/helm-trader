import { useState } from "react";
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
  onApprove: (symbol: string) => void;
  onAddActive: (symbol: string) => Promise<void>;
  onRemoveActive: (symbol: string) => Promise<void>;
}) {
  const [pick, setPick] = useState("BTCUSDT");
  if (!symbols) return <p className="muted">종목 목록을 불러오는 중…</p>;

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">유니버스</p>
          <h2>종목</h2>
          <p className="muted">코드를 외울 필요 없습니다. 검색해서 고르면 됩니다. 승인 전에는 엔진이 새 심볼을 구독하지 않습니다.</p>
        </div>
      </div>
      <form
        className="card toolbar"
        onSubmit={async (event) => {
          event.preventDefault();
          await onAddActive(pick);
        }}
      >
        <label>
          가동 목록에 추가
          <SymbolSearch value={pick} onChange={setPick} catalog={catalog} />
        </label>
        <button type="submit" className="primary">
          추가
        </button>
      </form>
      <div className="grid-3" style={{ marginTop: 14 }}>
        <article className="card">
          <h3>가동 중 · {symbols.active.length}</h3>
          <div className="chip-list">
            {symbols.active.length === 0 ? <span className="muted">없음</span> : null}
            {symbols.active.map((symbol) => (
              <span className="chip" key={symbol}>
                {symbol}
                <button type="button" className="danger" onClick={() => void onRemoveActive(symbol)}>
                  빼기
                </button>
              </span>
            ))}
          </div>
        </article>
        <article className="card">
          <h3>승인 대기 · {symbols.pending_approval.length}</h3>
          <div className="chip-list">
            {symbols.pending_approval.length === 0 ? <span className="muted">대기 없음</span> : null}
            {symbols.pending_approval.map((symbol) => (
              <span className="chip" key={symbol}>
                {symbol}
                <button type="button" className="primary" onClick={() => onApprove(symbol)}>
                  승인
                </button>
              </span>
            ))}
          </div>
        </article>
        <article className="card">
          <h3>블랙리스트 · {symbols.blacklist.length}</h3>
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
