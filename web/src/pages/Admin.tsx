import { useState } from "react";
import type { Me } from "../api";
import { LoadingBar } from "../LoadingBar";
import { formatInt } from "../format";

export function Admin({
  users,
  onApprove,
  onSuspend,
}: {
  users: Me[];
  onApprove: (id: number) => Promise<void>;
  onSuspend: (id: number) => Promise<void>;
}) {
  const [busy, setBusy] = useState("");
  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">관리</p>
          <h2>승인 큐</h2>
          <p className="muted">첫 관리자 이메일만 자동 승인됩니다. 나머지는 여기서 넣습니다. · {formatInt(users.length)}명</p>
        </div>
      </div>
      <LoadingBar show={Boolean(busy)} label={busy} />
      <div className="grid-3">
        {users.length === 0 ? <p className="muted">사용자가 없습니다.</p> : null}
        {users.map((user) => (
          <article className="card" key={user.id}>
            <h3>{user.nickname}</h3>
            <dl className="kv">
              <dt>이메일</dt>
              <dd>{user.email}</dd>
              <dt>상태</dt>
              <dd>
                <span className={`badge ${user.status === "approved" ? "good" : "warn"}`}>{user.status}</span>
              </dd>
              <dt>역할</dt>
              <dd>{user.role}</dd>
            </dl>
            <div className="actions" style={{ marginTop: 12 }}>
              {user.status !== "approved" ? (
                <button
                  type="button"
                  className="primary"
                  disabled={Boolean(busy)}
                  onClick={() => {
                    setBusy("승인 중…");
                    void onApprove(user.id).finally(() => setBusy(""));
                  }}
                >
                  승인
                </button>
              ) : (
                <button
                  type="button"
                  className="danger"
                  disabled={Boolean(busy)}
                  onClick={() => {
                    setBusy("정지 중…");
                    void onSuspend(user.id).finally(() => setBusy(""));
                  }}
                >
                  정지
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
