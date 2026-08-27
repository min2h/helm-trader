import { useEffect, useState } from "react";
import { api, type AutopilotState, type Me } from "./api";
import { formatMoney } from "./format";
import { pickDefaultSymbol } from "./pickSymbol";
import { LoadingBar } from "./LoadingBar";
import { SymbolSearch, type CatalogItem } from "./SymbolSearch";
import { Admin } from "./pages/Admin";
import { Autopilot } from "./pages/Autopilot";
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
  const [chartSymbol, setChartSymbol] = useState("");
  const [usdKrw, setUsdKrw] = useState(0);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [headlines, setHeadlines] = useState<Array<{ title: string }>>([]);
  const [users, setUsers] = useState<Me[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [error, setError] = useState("");
  const [pageLoading, setPageLoading] = useState(false);
  const [actionBusy, setActionBusy] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [mark, setMark] = useState<{ symbol: string; price: number | null } | null>(null);
  const [autopilot, setAutopilot] = useState<AutopilotState | null>(null);
  const aiLevel = String(params?.ai_level ?? "");

  async function loadMe() {
    try {
      setMe(await api.me());
      setError("");
    } catch {
      setMe(null);
    }
  }

  async function refresh(opts?: { silent?: boolean }) {
    if (!me || me.status !== "approved") return;
    if (!opts?.silent) setPageLoading(true);
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
      ...(chartSymbol
        ? [
            take(api.ticker(chartSymbol), (row) => {
              setMark(row);
              if (row.usd_krw) setUsdKrw(row.usd_krw);
            }),
          ]
        : []),
    ]);
    setError(errors[0] ?? "");
    if (!opts?.silent) setPageLoading(false);
  }

  async function runAction(label: string, fn: () => Promise<void>) {
    setActionBusy(label);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청에 실패했습니다.");
    } finally {
      setActionBusy("");
    }
  }

  async function loadChart(symbol: string) {
    setChartLoading(true);
    setChartError("");
    try {
      const res = await api.klines(symbol);
      setBars(res.bars);
      setChartError(res.error || (res.bars.length ? "" : "시세가 비어 있습니다."));
      if (res.bars.length) {
        const last = res.bars[res.bars.length - 1];
        setMark({ symbol, price: last.close });
      }
    } catch (err) {
      setBars([]);
      setChartError(err instanceof Error ? err.message : "시세를 불러오지 못했습니다.");
    } finally {
      setChartLoading(false);
    }
  }

  useEffect(() => {
    void loadMe();
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh({ silent: true }), 8000);
    return () => window.clearInterval(id);
  }, [me?.id, me?.status]);

  useEffect(() => {
    if (!me || me.status !== "approved") return;
    void api
      .catalog("all")
      .then((res) => {
        setCatalog(res.symbols);
        setChartSymbol((current) => {
          if (current) return current;
          return pickDefaultSymbol(res.symbols);
        });
      })
      .catch(() => setCatalog([]));
  }, [me?.id, me?.status]);

  useEffect(() => {
    if (!chartSymbol) return;
    void api
      .ticker(chartSymbol)
      .then((row) => {
        setMark(row);
        if (row.usd_krw) setUsdKrw(row.usd_krw);
      })
      .catch(() => undefined);
  }, [chartSymbol]);

  useEffect(() => {
    if (tab === "chart") {
      if (chartSymbol) void loadChart(chartSymbol);
    }
    if (tab === "invest" && me?.status === "approved") {
      void api.autopilot().then(setAutopilot).catch(() => setAutopilot(null));
      if (aiLevel !== "off") {
        void api.messages().then(setMessages).catch(() => undefined);
        void api.news().then(setHeadlines).catch(() => setHeadlines([]));
      } else {
        setMessages([]);
        setHeadlines([]);
      }
    }
    if (tab === "admin" && me?.role === "admin") {
      void api.adminUsers().then(setUsers).catch(() => undefined);
    }
  }, [tab, me?.id, jobs, chartSymbol, aiLevel]);

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
      <LoadingBar show={pageLoading || Boolean(actionBusy)} label={actionBusy || "불러오는 중…"} />
      {tab === "dash" ? (
        <Dashboard
          status={status}
          params={params}
          mark={mark}
          usdKrw={usdKrw}
          loading={pageLoading || Boolean(actionBusy)}
          onOpenSettings={() => setTab("settings")}
          onSoftStop={() =>
            runAction("소프트 정지 중…", async () => {
              await api.softStop();
              await refresh({ silent: true });
            })
          }
          onResume={() =>
            runAction("재개 중…", async () => {
              await api.resume();
              await refresh({ silent: true });
            })
          }
          onHardKill={async () => {
            if (!window.confirm("5초 안에 한 번 더 확인합니다. 전량 청산할까요?")) return;
            await runAction("전량 청산 확인 중…", async () => {
              const prepared = await api.prepareKill();
              if (!window.confirm("정말 전량 청산합니까?")) return;
              await api.confirmKill(prepared.token);
              await refresh({ silent: true });
            });
          }}
        />
      ) : null}
      {tab === "chart" ? (
        <section>
          <div className="page-head">
            <div>
              <p className="eyebrow">시세</p>
              <h2>차트</h2>
              <p className="muted">
                초록/빨간 가로선은 첫 번째 수동밴드의 상한·하한입니다.
                {mark?.price != null ? ` 지금 ${mark.symbol} ${formatMoney(mark.price, usdKrw, 2)}` : ""}
              </p>
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
                  void loadChart(symbol);
                }}
              />
            </label>
          </div>
          <LoadingBar show={chartLoading} label="시세를 불러오는 중…" />
          {bars.length ? (
            <ChartPanel
              bars={bars}
              lower={Number(jobs[0]?.lower || 0)}
              upper={Number(jobs[0]?.upper || 0)}
              light={theme === "light"}
            />
          ) : chartLoading ? null : (
            <p className="field-error">{chartError || "시세를 불러오지 못했습니다. 종목을 다시 골라 보세요."}</p>
          )}
        </section>
      ) : null}
      {tab === "invest" ? (
        <section>
          <div className="page-head">
            <div>
              <p className="eyebrow">실행</p>
              <h2>투자</h2>
              <p className="muted">
                왼쪽은 수동 밴드, 오른쪽은 AI 자동매매와 분석입니다. AI를 끄면 토큰을 전혀 쓰지 않습니다.
              </p>
            </div>
          </div>
          <div className="invest-layout">
            <ManualTrade
              compact
              usdKrw={usdKrw}
              jobs={jobs}
              catalog={catalog}
              onCreate={async (body) => {
                await api.createJob(body);
                await refresh({ silent: true });
              }}
              onToggle={async (id, enabled) => {
                await api.toggleJob(id, enabled);
                await refresh({ silent: true });
              }}
              onDelete={async (id) => {
                await api.deleteJob(id);
                await refresh({ silent: true });
              }}
            />
            <div className="stack-fields">
              <Autopilot
                state={autopilot}
                usdKrw={usdKrw}
                onSettings={() => setTab("settings")}
                onChanged={async () => {
                  await api
                    .autopilot()
                    .then(setAutopilot)
                    .catch(() => undefined);
                  await refresh({ silent: true });
                }}
                onReport={setReport}
              />
              <Chat
                compact
                aiOff={aiLevel === "off"}
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
          </div>
        </section>
      ) : null}
      {tab === "settings" ? (
        <Settings
          me={me}
          params={params}
          usdKrw={usdKrw}
          onPatch={async (key, value) => {
            await api.putParams({ [key]: value });
            await refresh({ silent: true });
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
            await refresh({ silent: true });
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
