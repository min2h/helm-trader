export function Symbols({
  symbols,
  onApprove,
}: {
  symbols: { active: string[]; pending_approval: string[]; blacklist: string[] } | null;
  onApprove: (symbol: string) => void;
}) {
  if (!symbols) return null;
  return (
    <section>
      <h2>종목</h2>
      <p>
        <strong>active</strong> {symbols.active.join(", ") || "없음"}
      </p>
      <p>
        <strong>pending</strong>
      </p>
      <ul>
        {symbols.pending_approval.length === 0 ? <li className="muted">대기 없음</li> : null}
        {symbols.pending_approval.map((symbol) => (
          <li key={symbol}>
            {symbol}{" "}
            <button type="button" onClick={() => onApprove(symbol)}>
              승인
            </button>
          </li>
        ))}
      </ul>
      <p className="muted">blacklist: {symbols.blacklist.join(", ")}</p>
    </section>
  );
}
