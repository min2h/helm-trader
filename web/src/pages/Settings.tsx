import { useState } from "react";
import type { Me } from "../api";
import { RadioGroup } from "../RadioGroup";

const GROUPS = [
  {
    key: "market_mode",
    options: [
      { value: "spot", label: "현물만" },
      { value: "futures", label: "선물만" },
      { value: "both", label: "현물+선물" },
    ],
  },
  {
    key: "symbol_selection",
    options: [
      { value: "ai_auto", label: "AI 추천 자동" },
      { value: "manual", label: "사용자 고정 목록" },
      { value: "ai_approve", label: "AI 추천 후 승인" },
    ],
  },
  {
    key: "strategy_mode",
    options: [
      { value: "trend", label: "추세추종" },
      { value: "funding_arb", label: "펀딩 차익" },
      { value: "grid", label: "횡보 그리드" },
      { value: "regime_auto", label: "레짐 자동선택" },
    ],
  },
  {
    key: "risk_grade",
    options: [
      { value: "conservative", label: "보수", hint: "1x / 회당 0.5%" },
      { value: "standard", label: "표준", hint: "2x / 회당 1%" },
      { value: "aggressive", label: "공격", hint: "3x / 회당 2%" },
    ],
  },
  {
    key: "ai_level",
    options: [
      { value: "off", label: "끔 (룰베이스)" },
      { value: "params_only", label: "일일 파라미터 제안" },
      { value: "params_and_symbols", label: "파라미터 + 종목 추천" },
    ],
  },
  {
    key: "stop_style",
    options: [
      { value: "fixed_pct", label: "고정 %" },
      { value: "atr", label: "ATR 배수" },
      { value: "trailing", label: "트레일링" },
    ],
  },
];

export function Settings({
  me,
  params,
  onPatch,
  onProfile,
  onSecrets,
}: {
  me: Me;
  params: Record<string, unknown>;
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

  return (
    <section>
      <h2>프로필</h2>
      <form
        className="band-form"
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
          <select
            value={me.theme}
            onChange={(e) => void onProfile({ theme: e.target.value })}
          >
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
        <button type="submit">프로필 저장</button>
      </form>

      <h2>개인 키 (쓰기 전용)</h2>
      <p className="muted">
        LLM {me.secrets.llm ? "설정됨" : "없음"} · Binance {me.secrets.binance ? "설정됨" : "없음"}. 저장된 키는 다시 보여주지 않습니다.
      </p>
      <form
        className="band-form"
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
        <button type="submit">키 저장</button>
      </form>

      <h2>라디오박스 설정</h2>
      <p className="muted">서버가 최종 검증한다. 목표 수익률 입력란은 없다.</p>
      {GROUPS.map((group) => (
        <RadioGroup
          key={group.key}
          name={group.key}
          value={String(params[group.key] ?? "")}
          options={group.options}
          onChange={(value) => onPatch(group.key, value)}
        />
      ))}
    </section>
  );
}
