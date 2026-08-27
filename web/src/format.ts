const INT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const DEC = (digits: number) =>
  new Intl.NumberFormat("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const KRW = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });

export function parseAmount(raw: string): number | null {
  const cleaned = raw.replace(/[$,₩,\s]/g, "").trim();
  if (!cleaned || cleaned === "-" || cleaned === ".") return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

export function formatInt(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return INT.format(n);
}

export function formatDecimal(value: unknown, digits = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return DEC(digits).format(n);
}

export function formatPct(value: unknown, digits = 2): string {
  return `${formatDecimal(value, digits)}%`;
}

export function formatUsd(value: unknown, digits = 2): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `$${DEC(digits).format(n)}`;
}

export function formatKrw(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `₩${KRW.format(Math.round(n))}원`;
}

export function formatMoney(usdt: unknown, usdKrw = 0, digits = 2): string {
  const n = Number(usdt);
  if (!Number.isFinite(n)) return "—";
  const usd = formatUsd(n, digits);
  if (!usdKrw) return usd;
  return `${usd} · ${formatKrw(n * usdKrw)}`;
}

export function formatUsdt(value: unknown, digits = 0, usdKrw = 0): string {
  return formatMoney(value, usdKrw, digits);
}

export function formatWhen(value: unknown): string {
  if (!value) return "아직 없음";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "medium" }).format(date);
}

export function isEmail(value: string): boolean {
  if (!value.trim()) return true;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}
