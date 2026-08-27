import { useEffect, useState } from "react";
import { api, type Me } from "./api";
import { SymbolSearch, type CatalogItem } from "./SymbolSearch";
import { Admin } from "./pages/Admin";
import { ChartPanel } from "./pages/ChartPanel";
import { Chat } from "./pages/Chat";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ManualTrade } from "./pages/ManualTrade";
import { Pending } from "./pages/Pending";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { Symbols } from "./pages/Symbols";

type Tab = "dash" | "chart" | "invest" | "settings" | "symbols" | "reports" | "admin";

export function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>("dash");
  const [params, setParams] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [symbols, setSymbols] = useState<{
    active: string[];
    pending_approval: string[];
    blacklist: string[];
  } | null>(null);
  const [report, setReport] = useState("");
  const [jobs, setJobs] = useState<Array<Record<string, unknown>>>([]);
  const [bars, setBars] = useState<Array<{ time: number; open: number; high: number; low: number; close: number }>>([]);
  const [chartSymbol, setChartSymbol] = useState("BTCUSDT");
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [headlines, setHeadlines] = useState<Array<{ title: string }>>([]);
  const [users, setUsers] = useState<Me[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [error, setError] = useState("");

  async function loadMe() {
    try {
      setMe(await api.me());
      setError("");
    } catch {
      setMe(null);
    }
  }

  async function refresh() {
    if (!me || me.status !== "approved") return;
    const errors: string[] = [];
    const take = async <T,>(job: Promise<T>, apply: (value: T) => void) => {
      try {
        apply(await job);
      } catch (err) {
        errors.push(err instanceof Error ? err.message : "load failed");
      }
    };
    await Promise.all([
      take(api.params(), setParams),
      take(api.status(), setStatus),
      take(api.symbols(), setSymbols),
      take(api.report(), (r) => setReport(r.markdown)),
      take(api.jobs(), setJobs),
    ]);
    setError(errors[0] ?? "");
  }

  useEffect(() => {
    void loadMe();
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(id);
  }, [me?.id, me?.status]);

  useEffect(() => {
    if (!me || me.status !== "approved") return;
    const market = String(params?.market_mode || "futures") === "spot" ? "spot" : "futures";
    void api.catalog(market).then((res) => setCatalog(res.symbols)).catch(() => setCatalog([]));
  }, [me?.id, me?.status, params?.market_mode]);

  useEffect(() => {
    if (tab === "chart") {
      const symbol = chartSymbol || String(jobs[0]?.symbol || "BTCUSDT");
      void api.klines(symbol).then((res) => setBars(res.bars)).catch(() => setBars([]));
    }
    if (tab === "invest" && me?.status === "approved") {
      void api.messages().then(setMessages).catch(() => undefined);
      void api.news().then(setHeadlines).catch(() => setHeadlines([]));
    }
    if (tab === "admin" && me?.role === "admin") {
      void api.adminUsers().then(setUsers).catch(() => undefined);
    }
  }, [tab, me?.id, jobs, chartSymbol]);

  const theme = me?.theme === "light" ? "light" : "dark";

  if (!me) {
    return (
      <div className={`shell ${theme}`}>
        <Login
          onDev={async (email) => {
            await api.devLogin(email, email.startsWith("admin"));
            await loadMe();
          }}
        />
      </div>
    );
  }

  if (me.status !== "approved") {
    return (
      <div className={`shell ${theme}`}>
        <Pending
          me={me}
          onLogout={async () => {
            await api.logout();
            setMe(null);
          }}
        />
      </div>
    );
  }

  const tabs: Array<[Tab, string, boolean]> = [
    ["dash", "현황", true],
    ["chart", "차트", true],
    ["invest", "투자", true],
    ["symbols", "종목", true],
    ["reports", "보고서", true],
    ["admin", "관리자", me.role === "admin"],
  ];

  async function replaceActive(next: string[]) {
    await api.putParams({ "symbols.active": next });
    await refresh();
  }

  return (
    <div className={`shell ${theme}`}>
      <header className="app-top">
        <div>
          <p className="brand-mark">helm-trader 0.2</p>
          <div className="identity">
            <h1>{me.nickname}</h1>
            <button type="button" className={tab === "settings" ? "on" : ""} onClick={() => setTab("settings")}>
              설정
            </button>
          </div>
          <p className="muted">{me.email}</p>
        </div>
        <div className="who">
          <div className="actions">
            <span className={`badge ${me.status === "approved" ? "good" : "warn"}`}>{me.status}</span>
            <button
              type="button"
              onClick={async () => {
                await api.logout();
                setMe(null);
              }}
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <nav className="nav">
        {tabs
          .filter(([, , show]) => show)
          .map(([id, label]) => (
            <button key={id} type="button" className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
      </nav>
      {error ? <p className="error">{error}</p> : null}
      {tab === "dash" ? (
        <Dashboard
          status={status}
          params={params}
          onOpenSettings={() => setTab("settings")}
          onSoftStop={async () => {
            await api.softStop();
            await refresh();
          }}
          onResume={async () => {
            await api.resume();
            await refresh();
          }}
          onHardKill={async () => {
            if (!window.confirm("5초 안에 한 번 더 확인합니다. 전량 청산할까요?")) return;
            const prepared = await api.prepareKill();
            if (!window.confirm("정말 전량 청산합니까?")) return;
            await api.confirmKill(prepared.token);
            await refresh();
          }}
        />
      ) : null}
      {tab === "chart" ? (
        <section>
          <div className="page-head">
            <div>
              <p className="eyebrow">시세</p>
              <h2>차트</h2>
              <p className="muted">초록/빨간 가로선은 첫 번째 수동밴드의 상한·하한입니다.</p>
            </div>
          </div>
          <div className="card toolbar">
            <label>
              종목
              <SymbolSearch
                value={chartSymbol}
                catalog={catalog}
                onChange={(symbol) => {
                  setChartSymbol(symbol);
                  void api.klines(symbol).then((res) => setBars(res.bars)).catch(() => setBars([]));
                }}
              />
            </label>
          </div>
          {bars.length ? (
            <ChartPanel
              bars={bars}
              lower={Number(jobs[0]?.lower || 0)}
              upper={Number(jobs[0]?.upper || 0)}
              light={theme === "light"}
            />
          ) : (
            <p className="muted">시세를 불러오지 못했습니다. 종목을 다시 골라 보세요.</p>
          )}
        </section>
      ) : null}
      {tab === "invest" ? (
        <section>
          <div className="page-head">
            <div>
              <p className="eyebrow">실행</p>
              <h2>투자</h2>
              <p className="muted">왼쪽은 수동 밴드, 오른쪽은 AI 분석입니다. AI는 주문을 내지 않습니다.</p>
            </div>
          </div>
          <div className="invest-layout">
            <ManualTrade
              compact
              jobs={jobs}
              catalog={catalog}
              onCreate={async (body) => {
                await api.createJob(body);
                await refresh();
              }}
              onToggle={async (id, enabled) => {
                await api.toggleJob(id, enabled);
                await refresh();
              }}
              onDelete={async (id) => {
                await api.deleteJob(id);
                await refresh();
              }}
            />
            <Chat
              compact
              messages={messages}
              headlines={headlines}
              hasKey={me.secrets.llm}
              onSend={async (text) => {
                const reply = await api.chat(text);
                setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: reply.content }]);
              }}
              onAnalyze={async () => {
                const result = await api.analyze();
                setReport(result.markdown);
                setHeadlines(result.headlines);
                setTab("reports");
              }}
            />
          </div>
        </section>
      ) : null}
      {tab === "settings" ? (
        <Settings
          me={me}
          params={params}
          onPatch={async (key, value) => {
            await api.putParams({ [key]: value });
            await refresh();
          }}
          onProfile={async (body) => {
            setMe(await api.patchMe(body));
          }}
          onSecrets={async (body) => {
            const flags = (await api.putSecrets(body)) as Me["secrets"];
            setMe({ ...me, secrets: flags });
          }}
        />
      ) : null}
      {tab === "symbols" ? (
        <Symbols
          symbols={symbols}
          catalog={catalog}
          onApprove={async (symbol) => {
            await api.approve(symbol);
            await refresh();
          }}
          onAddActive={async (symbol) => {
            const current = symbols?.active ?? [];
            if (current.includes(symbol)) return;
            await replaceActive([...current, symbol]);
          }}
          onRemoveActive={async (symbol) => {
            await replaceActive((symbols?.active ?? []).filter((item) => item !== symbol));
          }}
        />
      ) : null}
      {tab === "reports" ? <Reports markdown={report} /> : null}
      {tab === "admin" ? (
        <Admin
          users={users}
          onApprove={async (id) => {
            await api.approveUser(id);
            setUsers(await api.adminUsers());
          }}
          onSuspend={async (id) => {
            await api.suspendUser(id);
            setUsers(await api.adminUsers());
          }}
        />
      ) : null}
    </div>
  );
}
