from fastapi.testclient import TestClient

from helm.api.app import create_app
from helm.settings import Settings


def test_params_and_kill_switch(tmp_path) -> None:
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_catalog_warm=False,
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


def test_klines_do_not_500_when_binance_is_down(tmp_path, monkeypatch) -> None:
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_catalog_warm=False,
        helm_admin_emails="admin@local",
    )

    def boom(*_a, **_k):
        raise RuntimeError("ssl blocked")

    monkeypatch.setattr("helm.api.routes_status.fetch_klines", boom)
    client = TestClient(create_app(settings))
    client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    res = client.get("/api/market/klines?symbol=BTCUSDT")
    assert res.status_code == 200
    body = res.json()
    assert body["bars"] == []
    assert "ssl" in (body.get("error") or "").lower()


def test_catalog_reads_from_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "helm.research.catalog.fetch_full_catalog",
        lambda timeout=20.0: [
            {"symbol": "FOOUSDT", "base": "FOO", "quote": "USDT", "market": "spot", "status": "TRADING"},
            {"symbol": "FOOUSDT", "base": "FOO", "quote": "USDT", "market": "futures", "status": "TRADING"},
        ],
    )
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_admin_emails="admin@local",
        helm_catalog_warm=False,
    )
    client = TestClient(create_app(settings))
    res = client.get("/api/market/catalog?market=all")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 2
    assert {row["market"] for row in body["symbols"]} == {"spot", "futures"}
