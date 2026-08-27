from fastapi.testclient import TestClient

from helm.api.app import create_app
from helm.settings import Settings


def _client(tmp_path, admin_email: str = "admin@local"):
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_admin_emails=admin_email,
        helm_master_key="",
    )
    return TestClient(create_app(settings))


def test_pending_user_blocked_from_params(tmp_path) -> None:
    client = _client(tmp_path)
    guest = client.post("/api/auth/dev", json={"email": "guest@local"})
    assert guest.status_code == 200
    assert guest.json()["status"] == "pending"
    denied = client.get("/api/params")
    assert denied.status_code == 403
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["status"] == "pending"


def test_admin_approves_then_params_work(tmp_path) -> None:
    client = _client(tmp_path)
    client.post("/api/auth/dev", json={"email": "guest@local"})
    guest_cookie = client.cookies.get("helm_session")
    client.cookies.clear()
    admin = client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    assert admin.json()["role"] == "admin"
    users = client.get("/api/admin/users").json()
    guest = next(item for item in users if item["email"] == "guest@local")
    client.post(f"/api/admin/users/{guest['id']}/approve")
    client.cookies.clear()
    client.cookies.set("helm_session", guest_cookie)
    params = client.get("/api/params")
    assert params.status_code == 200
    patched = client.put("/api/params", json={"strategy_mode": "grid"})
    assert patched.json()["strategy_mode"] == "grid"


def test_secrets_are_write_only(tmp_path) -> None:
    client = _client(tmp_path)
    client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    flags = client.put(
        "/api/me/secrets",
        json={"llm_provider": "anthropic", "llm_key": "sk-test-secret"},
    )
    assert flags.json()["llm"] is True
    me = client.get("/api/me").json()
    assert "sk-test-secret" not in str(me)
