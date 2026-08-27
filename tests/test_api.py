from fastapi.testclient import TestClient

from helm.api.app import create_app
from helm.settings import Settings


def test_params_and_kill_switch(tmp_path) -> None:
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_admin_emails="admin@local",
    )
    client = TestClient(create_app(settings))
    denied = client.get("/api/params")
    assert denied.status_code == 401
    client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    params = client.get("/api/params")
    assert params.status_code == 200
    patched = client.put("/api/params", json={"strategy_mode": "grid"})
    assert patched.json()["strategy_mode"] == "grid"
    client.post("/api/control/soft-stop")
    assert client.get("/api/status").json()["run_state"] == "soft_stop"
    token = client.post("/api/control/hard-kill/prepare").json()["token"]
    killed = client.post("/api/control/hard-kill/confirm", json={"token": token})
    assert killed.json()["run_state"] == "hard_kill"
