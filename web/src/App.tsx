import { useEffect, useState } from "react";
import { api, type Me } from "./api";
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

type Tab = "dash" | "chart" | "manual" | "settings" | "symbols" | "reports" | "ai" | "admin";

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
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [headlines, setHeadlines] = useState<Array<{ title: string }>>([]);
  const [users, setUsers] = useState<Me[]>([]);
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
    try {
      const [p, s, sy, r, j] = await Promise.all([
        api.params(),
        api.status(),
        api.symbols(),
        api.report(),
        api.jobs(),
      ]);
      setParams(p);
      setStatus(s);
      setSymbols(sy);
      setReport(r.markdown);
      setJobs(j);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
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
    if (tab === "chart") {
      const symbol = String(jobs[0]?.symbol || "BTCUSDT");
      void api.klines(symbol).then((res) => setBars(res.bars)).catch(() => setBars([]));
    }
    if (tab === "ai" && me?.status === "approved") {
      void api.messages().then(setMessages).catch(() => undefined);
      void api.news().then(setHeadlines).catch(() => setHeadlines([]));
    }
    if (tab === "admin" && me?.role === "admin") {
      void api.adminUsers().then(setUsers).catch(() => undefined);
    }
  }, [tab, me?.id, jobs]);

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
    ["manual", "수동투자", true],
    ["settings", "설정", true],
    ["symbols", "종목", true],
    ["reports", "보고서", true],
    ["ai", "AI", true],
    ["admin", "관리자", me.role === "admin"],
  ];

  return (
    <div className={`shell ${theme}`}>
      <header>
        <div>
          <p className="eyebrow">helm-trader 0.2 · {me.status}</p>
          <h1>{me.nickname}</h1>
        </div>
        <button
          type="button"
          onClick={async () => {
            await api.logout();
            setMe(null);
          }}
        >
          로그아웃
        </button>
      </header>
      <nav>
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
          <h2>차트</h2>
          <p className="muted">노란/빨간 가로선은 첫 번째 수동밴드의 상한·하한입니다.</p>
          <label>
            심볼
            <input
              defaultValue={String(jobs[0]?.symbol || "BTCUSDT")}
              onBlur={(event) => {
                void api.klines(event.target.value).then((res) => setBars(res.bars)).catch(() => setBars([]));
              }}
            />
          </label>
          {bars.length ? (
            <ChartPanel
              bars={bars}
              lower={Number(jobs[0]?.lower || 0)}
              upper={Number(jobs[0]?.upper || 0)}
            />
          ) : (
            <p className="muted">시세를 불러오지 못했습니다. 심볼을 확인하고 입력란에서 포커스를 벗어나 보세요.</p>
          )}
        </section>
      ) : null}
      {tab === "manual" ? (
        <ManualTrade
          jobs={jobs}
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
      ) : null}
      {tab === "settings" && params ? (
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
          onApprove={async (symbol) => {
            await api.approve(symbol);
            await refresh();
          }}
        />
      ) : null}
      {tab === "reports" ? <Reports markdown={report} /> : null}
      {tab === "ai" ? (
        <Chat
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
      ) : null}
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
