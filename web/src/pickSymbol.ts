import type { CatalogItem } from "./SymbolSearch";

const PREFER = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];

export function pickDefaultSymbol(catalog: CatalogItem[]): string {
  for (const symbol of PREFER) {
    if (catalog.some((item) => item.symbol === symbol)) return symbol;
  }
  return catalog.find((item) => item.quote === "USDT")?.symbol || catalog[0]?.symbol || "";
}
