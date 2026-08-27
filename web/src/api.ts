async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text}`);
  }
  return response.json() as Promise<T>;
}

export type Me = {
  id: number;
  email: string;
  nickname: string;
  role: string;
  status: string;
  notify_email: boolean;
  notify_telegram: boolean;
  theme: string;
  min_equity_usdt: number;
  notify_address: string;
  secrets: {
    binance: boolean;
    llm: boolean;
    llm_provider: string;
    llm_hint?: string;
    binance_key_hint?: string;
    binance_secret_hint?: string;
  };
};

export type StoredSecrets = Me["secrets"] & {
  llm_key: string;
  binance_key: string;
  binance_secret: string;
};

export const api = {
  me: () => request<Me>("/api/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  devLogin: (email: string, admin = false) =>
    request<Me>("/api/auth/dev", { method: "POST", body: JSON.stringify({ email, admin }) }),
  patchMe: (body: Record<string, unknown>) =>
    request<Me>("/api/me", { method: "PATCH", body: JSON.stringify(body) }),
  getSecrets: () => request<StoredSecrets>("/api/me/secrets"),
  putSecrets: (body: Record<string, string>) =>
    request<Me["secrets"]>("/api/me/secrets", { method: "PUT", body: JSON.stringify(body) }),
  params: () => request<Record<string, unknown>>("/api/params"),
  putParams: (patch: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/params", { method: "PUT", body: JSON.stringify(patch) }),
  status: () => request<Record<string, unknown>>("/api/status"),
  symbols: () => request<{ active: string[]; pending_approval: string[]; blacklist: string[] }>("/api/symbols"),
  approve: (symbol: string) =>
    request("/api/symbols/approve", { method: "POST", body: JSON.stringify({ symbol }) }),
  softStop: () => request("/api/control/soft-stop", { method: "POST" }),
  resume: () => request("/api/control/resume", { method: "POST" }),
  prepareKill: () => request<{ token: string }>("/api/control/hard-kill/prepare", { method: "POST" }),
  confirmKill: (token: string) =>
    request("/api/control/hard-kill/confirm", { method: "POST", body: JSON.stringify({ token }) }),
  report: () => request<{ markdown: string; kind?: string }>("/api/reports/latest"),
  jobs: () => request<Array<Record<string, unknown>>>("/api/manual-jobs"),
  createJob: (body: Record<string, unknown>) =>
    request("/api/manual-jobs", { method: "POST", body: JSON.stringify(body) }),
  toggleJob: (id: number, enabled: boolean) =>
    request(`/api/manual-jobs/${id}/toggle`, { method: "POST", body: JSON.stringify({ enabled }) }),
  deleteJob: (id: number) => request(`/api/manual-jobs/${id}`, { method: "DELETE" }),
  catalog: (market = "all") =>
    request<{
      count: number;
      symbols: Array<{ symbol: string; base: string; quote: string; market?: string }>;
    }>(`/api/market/catalog?market=${market}`),
  ticker: (symbol: string) =>
    request<{
      symbol: string;
      price: number | null;
      usd_krw?: number;
      price_krw?: number | null;
      error?: string | null;
    }>(`/api/market/ticker?symbol=${symbol}`),
  klines: (symbol: string) =>
    request<{
      bars: Array<{ time: number; open: number; high: number; low: number; close: number }>;
      source?: string | null;
      error?: string | null;
    }>(`/api/market/klines?symbol=${symbol}`),
  chat: (message: string) =>
    request<{ content: string }>("/api/ai/chat", { method: "POST", body: JSON.stringify({ message }) }),
  messages: () => request<Array<{ role: string; content: string }>>("/api/ai/messages"),
  analyze: () => request<{ markdown: string; headlines: Array<{ title: string }> }>("/api/ai/analyze", { method: "POST" }),
  news: () => request<Array<{ title: string; link: string }>>("/api/ai/news"),
  adminUsers: () => request<Me[]>("/api/admin/users"),
  approveUser: (id: number) => request(`/api/admin/users/${id}/approve`, { method: "POST" }),
  suspendUser: (id: number) => request(`/api/admin/users/${id}/suspend`, { method: "POST" }),
};
