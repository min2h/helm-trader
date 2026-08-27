import { useState } from "react";

const PRESETS = [
  "지금 레짐은 추세인가 횡보인가? 4개 시나리오로 답해줘.",
  "내 손절 거리와 회당 리스크가 맞는지 점검해줘. 레버리지는 올리지 마.",
  "오늘 뉴스가 롱에 불리한 심볼이 있으면 블랙리스트 후보만 말해줘.",
  "펀딩비가 캐리를 잠식하면 어떻게 해야 하나? 주문은 내지 마.",
];

export function Chat({
  messages,
  headlines,
  onSend,
  onAnalyze,
  hasKey,
}: {
  messages: Array<{ role: string; content: string }>;
  headlines: Array<{ title: string }>;
  onSend: (text: string) => Promise<void>;
  onAnalyze: () => Promise<void>;
  hasKey: boolean;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <section>
      <h2>AI 분석</h2>
      <p className="muted">시스템 프롬프트는 모든 질문에 강제됩니다. AI는 주문을 내지 않습니다.</p>
      {!hasKey ? (
        <p className="state-banner soft_stop">설정 → 개인 LLM 키를 넣어야 분석이 됩니다. 그 전까지는 수동투자 탭을 쓰세요.</p>
      ) : (
        <>
          <div className="actions">
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await onAnalyze();
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "분석 중…" : "심층 자동분석 (시세+펀딩+뉴스)"}
            </button>
          </div>
          <h3>헤드라인</h3>
          <ul className="news">
            {headlines.length === 0 ? <li className="muted">아직 없음</li> : null}
            {headlines.map((item) => (
              <li key={item.title}>{item.title}</li>
            ))}
          </ul>
          <div className="presets">
            {PRESETS.map((item) => (
              <button key={item} type="button" onClick={() => setText(item)}>
                {item}
              </button>
            ))}
          </div>
          <div className="chat">
            {messages.map((msg, idx) => (
              <article key={idx} className={msg.role}>
                <strong>{msg.role === "user" ? "나" : "애널리스트"}</strong>
                <pre>{msg.content}</pre>
              </article>
            ))}
          </div>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (!text.trim() || busy) return;
              setBusy(true);
              try {
                await onSend(text);
                setText("");
              } finally {
                setBusy(false);
              }
            }}
          >
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="예: BTC 15분봉 추세가 꺾이면 어떤 시나리오를 보나?"
            />
            <button type="submit" className="primary" disabled={busy}>
              질문 보내기
            </button>
          </form>
        </>
      )}
    </section>
  );
}
