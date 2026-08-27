import { useState } from "react";
import type { Me } from "../api";
import { RadioGroup } from "../RadioGroup";

const GROUPS = [
  {
    key: "market_mode",
    title: "시장",
    hint: "AI는 이 값을 바꿀 수 없습니다. 한국 계정은 선물 가능 여부를 먼저 확인하세요.",
    options: [
      { value: "spot", label: "현물만" },
      { value: "futures", label: "선물만" },
      { value: "both", label: "현물+선물" },
    ],
  },
  {
    key: "symbol_selection",
    title: "종목 선택",
    hint: "AI 추천 후 승인 모드면 대기 종목은 종목 탭에서 직접 넣습니다.",
    options: [
      { value: "ai_auto", label: "AI 추천 자동" },
      { value: "manual", label: "사용자 고정 목록" },
      { value: "ai_approve", label: "AI 추천 후 승인" },
    ],
  },
  {
    key: "strategy_mode",
    title: "전략",
    hint: "실행은 룰베이스입니다. AI는 파라미터만 제안합니다.",
    options: [
      { value: "trend", label: "추세추종" },
      { value: "funding_arb", label: "펀딩 차익" },
      { value: "grid", label: "횡보 그리드" },
      { value: "regime_auto", label: "레짐 자동선택" },
    ],
  },
  {
    key: "risk_grade",
    title: "리스크 등급",
    hint: "목표 수익률은 없습니다. 등급이 레버리지·회당 리스크를 채웁니다.",
    options: [
      { value: "conservative", label: "보수", hint: "1x / 회당 0.5%" },
      { value: "standard", label: "표준", hint: "2x / 회당 1%" },
      { value: "aggressive", label: "공격", hint: "3x / 회당 2%" },
    ],
  },
  {
    key: "ai_level",
    title: "AI 개입",
    hint: "꺼도 마지막 파라미터가 그대로 돕니다.",
    options: [
      { value: "off", label: "끔 (룰베이스)" },
      { value: "params_only", label: "일일 파라미터 제안" },
      { value: "params_and_symbols", label: "파라미터 + 종목 추천" },
    ],
  },
  {
    key: "stop_style",
    title: "손절 방식",
    hint: "거래소 StopMarket + close_position이 최종 안전망입니다.",
    options: [
      { value: "fixed_pct", label: "고정 %" },
      { value: "atr", label: "ATR 배수" },
      { value: "trailing", label: "트레일링" },
    ],
  },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function Settings({
  me,
  params,
  onPatch,
  onProfile,
  onSecrets,
}: {
  me: Me;
  params: Record<string, unknown> | null;
  onPatch: (key: string, value: string) => void;
  onProfile: (body: Record<string, unknown>) => Promise<void>;
  onSecrets: (body: Record<string, string>) => Promise<void>;
}) {
  const [nickname, setNickname] = useState(me.nickname);
  const [emailAddr, setEmailAddr] = useState(me.notify_address);
  const [minEq, setMinEq] = useState(String(me.min_equity_usdt));
  const [llmKey, setLlmKey] = useState("");
  const [llmProvider, setLlmProvider] = useState(me.secrets.llm_provider || "anthropic");
  const [binanceKey, setBinanceKey] = useState("");
  const [binanceSecret, setBinanceSecret] = useState("");
  const risk = asRecord(params?.risk);
  const strategy = asRecord(params?.strategy);
  const trend = asRecord(strategy.trend);
  const funding = asRecord(strategy.funding_arb);
  const grid = asRecord(strategy.grid);

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">계정 · 키 · 매매</p>
          <h2>설정</h2>
        </div>
      </div>

      <div className="grid-2">
        <form
          className="card stack-fields"
          onSubmit={async (event) => {
            event.preventDefault();
            await onProfile({
              nickname,
              notify_address: emailAddr,
              min_equity_usdt: Number(minEq),
              notify_email: me.notify_email,
              notify_telegram: me.notify_telegram,
              theme: me.theme,
            });
          }}
        >
          <h3>프로필</h3>
          <div className="form-grid">
            <label>
              닉네임
              <input value={nickname} onChange={(e) => setNickname(e.target.value)} />
            </label>
            <label>
              알림 이메일
              <input value={emailAddr} onChange={(e) => setEmailAddr(e.target.value)} />
            </label>
            <label>
              청산방지 MIN USDT
              <input value={minEq} onChange={(e) => setMinEq(e.target.value)} />
            </label>
            <label>
              테마
              <select value={me.theme} onChange={(e) => void onProfile({ theme: e.target.value })}>
                <option value="dark">다크</option>
                <option value="light">라이트</option>
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={me.notify_email}
                onChange={(e) => void onProfile({ notify_email: e.target.checked })}
              />
              이메일 알림
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={me.notify_telegram}
                onChange={(e) => void onProfile({ notify_telegram: e.target.checked })}
              />
              텔레그램 알림
            </label>
          </div>
          <button type="submit" className="primary">
            프로필 저장
          </button>
        </form>

        <form
          className="card stack-fields"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSecrets({
              llm_provider: llmProvider,
              llm_key: llmKey,
              binance_key: binanceKey,
              binance_secret: binanceSecret,
            });
            setLlmKey("");
            setBinanceKey("");
            setBinanceSecret("");
          }}
        >
          <h3>개인 키 (쓰기 전용)</h3>
          <div className="key-status">
            <span className={`badge ${me.secrets.llm ? "good" : "warn"}`}>
              LLM {me.secrets.llm ? "설정됨" : "없음"}
            </span>
            <span className={`badge ${me.secrets.binance ? "good" : "warn"}`}>
              Binance {me.secrets.binance ? "설정됨" : "없음"}
            </span>
          </div>
          <p className="muted">저장된 키는 다시 보여주지 않습니다. 서버 `.env`가 아니라 여기만 씁니다.</p>
          <div className="form-grid">
            <label>
              LLM
              <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
                <option value="anthropic">Anthropic</option>
                <option value="openai">OpenAI</option>
              </select>
            </label>
            <label>
              LLM API 키
              <input type="password" value={llmKey} onChange={(e) => setLlmKey(e.target.value)} />
            </label>
            <label>
              Binance key
              <input type="password" value={binanceKey} onChange={(e) => setBinanceKey(e.target.value)} />
            </label>
            <label>
              Binance secret
              <input type="password" value={binanceSecret} onChange={(e) => setBinanceSecret(e.target.value)} />
            </label>
          </div>
          <button type="submit" className="primary">
            키 저장
          </button>
        </form>
      </div>

      <div className="page-head">
        <div>
          <h2>매매 설정</h2>
          <p className="muted">서버가 최종 검증합니다. 목표 수익률 입력란은 없습니다.</p>
        </div>
      </div>
      {params ? (
        <div className="grid-2">
          {GROUPS.map((group) => (
            <RadioGroup
              key={group.key}
              name={group.key}
              title={group.title}
              hint={group.hint}
              value={String(params[group.key] ?? "")}
              options={group.options}
              onChange={(value) => onPatch(group.key, value)}
            />
          ))}
        </div>
      ) : (
        <p className="muted">매매 파라미터를 불러오는 중…</p>
      )}

      <div className="page-head">
        <div>
          <h2>현재 적용 숫자</h2>
          <p className="muted">읽기 전용입니다. 등급·AI 배치가 이 값을 채웁니다.</p>
        </div>
      </div>
      <div className="grid-stats">
        <article className="stat">
          <dt>레버리지</dt>
          <dd>{String(risk.leverage ?? "—")}x</dd>
        </article>
        <article className="stat">
          <dt>회당 리스크</dt>
          <dd>{String(risk.per_trade_risk_pct ?? "—")}%</dd>
        </article>
        <article className="stat">
          <dt>일일 손실 한도</dt>
          <dd>{String(risk.daily_loss_limit_pct ?? "—")}%</dd>
        </article>
        <article className="stat">
          <dt>포트폴리오 MDD 킬</dt>
          <dd>{String(risk.portfolio_mdd_kill_pct ?? "—")}%</dd>
        </article>
        <article className="stat">
          <dt>동시 포지션</dt>
          <dd>{String(risk.max_concurrent_positions ?? "—")}</dd>
        </article>
        <article className="stat">
          <dt>MIN 잔고</dt>
          <dd>{String(risk.min_equity_usdt ?? me.min_equity_usdt)}</dd>
        </article>
      </div>

      <div className="grid-3" style={{ marginTop: 14 }}>
        <article className="card">
          <h3>추세추종</h3>
          <dl className="kv">
            <dt>봉</dt>
            <dd>{String(trend.timeframe ?? "—")}</dd>
            <dt>Donchian</dt>
            <dd>{String(trend.donchian_n ?? "—")}</dd>
            <dt>ATR n</dt>
            <dd>{String(trend.atr_n ?? "—")}</dd>
            <dt>ATR 배수</dt>
            <dd>{String(trend.atr_stop_mult ?? "—")}</dd>
            <dt>최소 ADX</dt>
            <dd>{String(trend.min_adx ?? "—")}</dd>
          </dl>
        </article>
        <article className="card">
          <h3>펀딩 차익</h3>
          <dl className="kv">
            <dt>최소 APR</dt>
            <dd>{String(funding.min_funding_apr ?? "—")}</dd>
            <dt>베이시스</dt>
            <dd>{String(funding.max_basis_bps ?? "—")} bps</dd>
            <dt>리밸런스</dt>
            <dd>{String(funding.rebalance_threshold_bps ?? "—")} bps</dd>
          </dl>
        </article>
        <article className="card">
          <h3>그리드</h3>
          <dl className="kv">
            <dt>봉</dt>
            <dd>{String(grid.timeframe ?? "—")}</dd>
            <dt>ATR 배수</dt>
            <dd>{String(grid.grid_atr_mult ?? "—")}</dd>
            <dt>레벨</dt>
            <dd>{String(grid.levels ?? "—")}</dd>
            <dt>재고 한도</dt>
            <dd>{String(grid.max_inventory_pct ?? "—")}%</dd>
          </dl>
        </article>
      </div>
    </section>
  );
}
