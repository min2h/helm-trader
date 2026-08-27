import type { Me } from "../api";

export function Pending({ me, onLogout }: { me: Me; onLogout: () => void }) {
  return (
    <section className="auth-card">
      <p className="eyebrow">access requested</p>
      <h1>{me.nickname}님, 승인 대기 중입니다</h1>
      <p className="muted">{me.email} — 관리자가 승인하기 전에는 매매·AI를 쓸 수 없습니다.</p>
      <button type="button" onClick={onLogout}>
        로그아웃
      </button>
    </section>
  );
}
