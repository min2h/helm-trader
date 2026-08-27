import type { Me } from "../api";

export function Admin({
  users,
  onApprove,
  onSuspend,
}: {
  users: Me[];
  onApprove: (id: number) => Promise<void>;
  onSuspend: (id: number) => Promise<void>;
}) {
  return (
    <section>
      <h2>승인 큐</h2>
      <table className="users">
        <thead>
          <tr>
            <th>닉네임</th>
            <th>이메일</th>
            <th>상태</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.nickname}</td>
              <td>{user.email}</td>
              <td>{user.status}</td>
              <td>
                {user.status !== "approved" ? (
                  <button type="button" onClick={() => void onApprove(user.id)}>
                    승인
                  </button>
                ) : (
                  <button type="button" className="danger" onClick={() => void onSuspend(user.id)}>
                    정지
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
