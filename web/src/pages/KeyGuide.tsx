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
    title: "Binance API (설정 화면)",
    site: "https://www.binance.com/en/my/settings/api-management",
    steps: [
      "Binance 로그인 → 프로필 → API Management → Create API",
      "권한은 읽기 + 선물/현물 거래만. 출금(Enable Withdrawals)은 끄기",
      "IP 액세스 제한에 이 PC 공인 IP",
      "Key / Secret을 설정 → 개인 키에 저장. GitHub/.env에 넣지 말 것",
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
      <p className="muted">서버 키는 이 PC의 `.env`에만 둡니다. Binance·LLM 키는 아래 설정 칸에만 둡니다.</p>
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
