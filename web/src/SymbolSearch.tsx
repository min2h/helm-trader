import { useMemo, useState } from "react";

export type CatalogItem = { symbol: string; base: string; quote: string; market?: string };

const KO_BASE: Record<string, string> = {
  비트코인: "BTC",
  비트: "BTC",
  이더리움: "ETH",
  이더: "ETH",
  솔라나: "SOL",
  리플: "XRP",
  도지: "DOGE",
  에이다: "ADA",
  아발란체: "AVAX",
  링크: "LINK",
  수이: "SUI",
  톤: "TON",
};

function haystack(item: CatalogItem): string {
  return `${item.symbol} ${item.base} ${item.quote}`.toUpperCase();
}

function queryTokens(raw: string): string[] {
  const q = raw.trim();
  if (!q) return [];
  const mapped = KO_BASE[q] || KO_BASE[q.replace(/\s+/g, "")];
  return [q.toUpperCase(), mapped].filter(Boolean) as string[];
}

export function SymbolSearch({
  value,
  onChange,
  catalog,
  placeholder = "BTC, 비트코인, ETHUSDT…",
}: {
  value: string;
  onChange: (symbol: string) => void;
  catalog: CatalogItem[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const tokens = queryTokens(query || value);
  const matches = useMemo(() => {
    const list = catalog.length ? catalog : [{ symbol: value || "BTCUSDT", base: "BTC", quote: "USDT" }];
    if (!tokens.length) return list.slice(0, 12);
    return list
      .filter((item) => tokens.some((token) => haystack(item).includes(token)))
      .slice(0, 20);
  }, [catalog, tokens, value]);

  return (
    <div className="symbol-search">
      <input
        value={open ? query : value}
        placeholder={placeholder}
        autoComplete="off"
        onFocus={() => {
          setQuery(value);
          setOpen(true);
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open ? (
        <ul className="symbol-menu">
          {matches.length === 0 ? <li className="muted">검색 결과 없음</li> : null}
          {matches.map((item) => (
            <li key={`${item.market || "m"}-${item.symbol}`}>
              <button
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(item.symbol);
                  setQuery(item.symbol);
                  setOpen(false);
                }}
              >
                <strong>{item.symbol}</strong>
                <span className="muted">
                  {item.base}/{item.quote}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
