export function Login({ onDev }: { onDev: (email: string) => void }) {
  return (
    <section className="auth-card">
      <p className="eyebrow">helm-trader v0.2</p>
      <h1>로그인 후 관리자 승인</h1>
      <ol className="steps">
        <li>Google 로그인 또는 아래 로컬 입장</li>
        <li>관리자가 승인할 때까지 대기</li>
        <li>계정명 옆 설정에서 닉네임·MIN 잔고·(선택) 개인 LLM 키</li>
        <li>투자 탭: 왼쪽 수동밴드, 오른쪽 AI 분석</li>
      </ol>
      <div className="oauth">
        <a className="btn google" href="/api/auth/google/login">
          Google로 계속
        </a>
      </div>
      <div className="dev-login">
        <p className="muted">Google 버튼이 안 되면 아래 로컬 입장만 씁니다.</p>
        <div className="actions">
          <button type="button" className="primary" onClick={() => onDev("admin@local")}>
            관리자로 바로 입장
          </button>
          <button type="button" onClick={() => onDev("guest@local")}>
            게스트(승인 대기)로 입장
          </button>
        </div>
      </div>
    </section>
  );
}
