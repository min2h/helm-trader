const BINANCE_GUIDE = {
  title: "Binance API 생성 (이 PC 설정 화면에 넣음)",
  site: "https://www.binance.com/en/my/settings/api-management",
  before: [
    "Binance 계정 · 본인인증(KYC) · 2단계 인증(2FA)이 되어 있어야 합니다.",
    "선물을 쓸 거면 웹에서 USDⓈ-M 선물 계정을 먼저 개설하세요. 키를 만든 뒤에 선물 계정을 열면 권한이 빠질 수 있습니다.",
    "한국 계정은 선물 이용 가능 여부를 먼저 확인하세요.",
  ],
  steps: [
    "브라우저에서 Binance에 로그인합니다.",
    "오른쪽 위 프로필 → API Management. 바로 가기: 아래 링크.",
    "Create API → System-generated(시스템 생성)를 고릅니다. Self-generated는 하드웨어 키용입니다.",
    "이름 예: helm-trader. 어디에 쓰는지 바로 보이게 적습니다.",
    "이메일 · 인증앱 · 패스키 등 보안 확인을 끝냅니다.",
    "권한: Enable Reading(읽기) 켜기. 현물이면 Enable Spot & Margin Trading. 선물이면 Enable Futures. 둘 다 쓰면 둘 다 켭니다.",
    "절대 끄지 말고 꺼 둘 것: Enable Withdrawals(출금), Enable Internal Transfer, Enable Universal Transfer.",
    "Restrict access to trusted IPs only(신뢰 IP만). Unrestricted는 90일 만료·덜 안전합니다.",
    "이 PC의 공인 IP를 넣습니다. 확인: https://api.ipify.org  공유기 IP가 바뀌면 여기도 수정합니다.",
    "API Key와 Secret Key를 바로 복사합니다. Secret은 보통 한 번만 보입니다.",
    "이 화면 위쪽 Binance key / secret에 붙여넣고 키 저장. GitHub·채팅·.env에는 넣지 않습니다.",
  ],
  after: [
    "저장 후 배지가 Binance 설정됨이 되고, 보기/숨기기로 확인할 수 있습니다.",
    "실주문은 아직 엔진 연결 전입니다. 키는 이후 체결용으로 DB에만 둡니다.",
  ],
};

const KEYS = [
  {
    title: "Google 로그인 (서버 .env)",
    site: "https://console.cloud.google.com/apis/credentials",
    steps: [
      "Google Cloud에서 프로젝트 생성 → API 및 서비스 → 사용자 인증 정보",
      "OAuth 동의 화면: 외부 / 테스트 사용자에 본인 Gmail",
      "OAuth 클라이언트 ID: 웹 애플리케이션",
      "승인된 JS 원본: http://127.0.0.1:8090",
      "승인된 리디렉션: http://127.0.0.1:8090/api/auth/google/callback",
      ".env에 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET",
    ],
  },
  {
    title: "Anthropic LLM (설정 화면, 선택)",
    site: "https://console.anthropic.com/settings/keys",
    steps: ["계정 생성 후 API Keys → Create Key", "설정 → LLM=Anthropic 에 붙여넣기"],
  },
  {
    title: "OpenAI LLM (설정 화면, 선택)",
    site: "https://platform.openai.com/api-keys",
    steps: ["API keys → Create new secret key", "설정 → LLM=OpenAI 에 붙여넣기"],
  },
  {
    title: "텔레그램 봇 (서버 .env, 선택)",
    site: "https://t.me/BotFather",
    steps: ["/newbot 으로 봇 생성", "받은 토큰을 TELEGRAM_BOT_TOKEN", "본인 채팅에서 봇을 연 뒤 TELEGRAM_CHAT_ID"],
  },
  {
    title: "Gmail 앱 비밀번호 SMTP (서버 .env, 선택)",
    site: "https://myaccount.google.com/apppasswords",
    steps: ["2단계 인증 켠 뒤 앱 비밀번호 발급", "SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USER=지메일, SMTP_PASSWORD=앱비밀번호"],
  },
  {
    title: "마스터 키 (서버 .env)",
    site: "",
    steps: [
      "개인 키 암호화를 위해 한 번 생성: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
      "나온 값을 HELM_MASTER_KEY에 넣고 바꾸지 말 것",
    ],
  },
];

export function KeyGuide() {
  return (
    <article className="card stack-fields" style={{ marginTop: 14 }}>
      <h3>키 발급 사이트 / 방법</h3>
      <p className="muted">서버 키는 이 PC의 `.env`에만 둡니다. Binance·LLM 키는 위 설정 칸에만 둡니다.</p>

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
        <p className="muted">{BINANCE_GUIDE.after.join(" ")}</p>
      </section>

      <div className="grid-2">
        {KEYS.map((item) => (
          <section key={item.title} className="help-card">
            <h3>{item.title}</h3>
            {item.site ? (
              <p>
                <a href={item.site} target="_blank" rel="noreferrer">
                  {item.site}
                </a>
              </p>
            ) : null}
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
