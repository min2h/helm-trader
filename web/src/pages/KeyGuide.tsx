const BINANCE_GUIDE = {
  title: "Binance API 만들기",
  site: "https://www.binance.com/en/my/settings/api-management",
  before: [
    "Binance 계정, 본인인증, 2단계 인증이 되어 있어야 합니다.",
    "선물을 쓸 거면 Binance에서 USDⓈ-M 선물 계정을 먼저 여세요.",
    "만든 키는 위쪽 Binance key / secret에만 붙여넣습니다.",
  ],
  steps: [
    "Binance에 로그인합니다.",
    "오른쪽 위 프로필 → API Management. 바로 가기는 아래 링크입니다.",
    "Create API → System-generated(시스템 생성)를 고릅니다.",
    "이름 예: helm-trader.",
    "이메일 · 인증앱 확인을 끝냅니다.",
    "권한: Enable Reading(읽기) 켜기. 현물이면 Enable Spot & Margin Trading. 선물이면 Enable Futures.",
    "출금(Enable Withdrawals)과 이체(Transfer)는 끕니다.",
    "Restrict access to trusted IPs only(이 PC IP만). IP 확인: https://api.ipify.org",
    "API Key와 Secret Key를 바로 복사합니다. Secret은 한 번만 보이는 경우가 많습니다.",
    "위쪽 칸에 붙여넣고 키 저장을 누릅니다. 다른 사람이나 채팅에 보내지 마세요.",
  ],
  after: "저장되면 Binance 설정됨 배지가 켜집니다. 보기/숨기기로 확인할 수 있습니다.",
};

const USER_KEYS = [
  {
    title: "Anthropic (선택, AI 분석)",
    site: "https://console.anthropic.com/settings/keys",
    steps: ["계정 만든 뒤 API Keys → Create Key", "위쪽 LLM을 Anthropic으로 고르고 키를 붙여넣은 다음 키 저장"],
  },
  {
    title: "OpenAI (선택, AI 분석)",
    site: "https://platform.openai.com/api-keys",
    steps: ["API keys → Create new secret key", "위쪽 LLM을 OpenAI로 고르고 키를 붙여넣은 다음 키 저장"],
  },
];

export function KeyGuide() {
  return (
    <article className="card stack-fields" style={{ marginTop: 14 }}>
      <h3>키 만드는 방법</h3>
      <p className="muted">여기서 넣는 키는 이 계정에만 저장됩니다. 로그인용 Google 설정은 관리자가 이미 해 둡니다.</p>

      <section className="help-card">
        <h3>{BINANCE_GUIDE.title}</h3>
        <p>
          <a href={BINANCE_GUIDE.site} target="_blank" rel="noreferrer">
            {BINANCE_GUIDE.site}
          </a>
        </p>
        <ul className="steps">
          {BINANCE_GUIDE.before.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <ol className="steps">
          {BINANCE_GUIDE.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <p className="muted">{BINANCE_GUIDE.after}</p>
      </section>

      <div className="grid-2">
        {USER_KEYS.map((item) => (
          <section key={item.title} className="help-card">
            <h3>{item.title}</h3>
            <p>
              <a href={item.site} target="_blank" rel="noreferrer">
                {item.site}
              </a>
            </p>
            <ol className="steps">
              {item.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </article>
  );
}
