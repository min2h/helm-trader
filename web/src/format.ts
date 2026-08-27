const INT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const DEC = (digits: number) =>
  new Intl.NumberFormat("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function parseAmount(raw: string): number | null {
  const cleaned = raw.replace(/,/g, "").trim();
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

export function formatUsdt(value: unknown, digits = 0): string {
  return `${formatDecimal(value, digits)} USDT`;
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
