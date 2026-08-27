import { useMemo, useState } from "react";

export type CatalogItem = { symbol: string; base: string; quote: string; market?: string };

const KO_QUERY: Record<string, string> = {
  비트코인: "BTC",
  비트: "BTC",
  이더리움: "ETH",
  이더: "ETH",
  솔라나: "SOL",
  리플: "XRP",
  도지: "DOGE",
};

function haystack(item: CatalogItem): string {
  return `${item.symbol} ${item.base} ${item.quote} ${item.market || ""}`.toUpperCase();
}

function queryTokens(raw: string): string[] {
  const q = raw.trim();
  if (!q) return [];
  const mapped = KO_QUERY[q] || KO_QUERY[q.replace(/\s+/g, "")];
  return [q.toUpperCase(), mapped].filter(Boolean) as string[];
}

function marketLabel(market?: string): string {
  if (market === "spot") return "현물";
  if (market === "futures") return "선물";
  return "";
}

export function SymbolSearch({
  value,
  onChange,
  catalog,
  placeholder = "심볼 검색 (BTC, ETHUSDT, 비트코인)",
}: {
  value: string;
  onChange: (symbol: string) => void;
  catalog: CatalogItem[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const tokens = queryTokens(query);
  const matches = useMemo(() => {
    if (!catalog.length) return [];
    if (!tokens.length) return catalog.slice(0, 40);
    return catalog.filter((item) => tokens.some((token) => haystack(item).includes(token))).slice(0, 80);
  }, [catalog, tokens]);

  return (
    <div className="symbol-search">
      <input
        value={open ? query : value}
        placeholder={placeholder}
        autoComplete="off"
        onFocus={() => {
          setQuery("");
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
          <li className="muted">
            {catalog.length ? `${catalog.length.toLocaleString("en-US")}종 조회 · 검색어를 입력하세요` : "종목 목록을 불러오는 중…"}
          </li>
          {matches.length === 0 && catalog.length ? <li className="muted">검색 결과 없음</li> : null}
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
                  {marketLabel(item.market)} {item.base}/{item.quote}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
