from fastapi.testclient import TestClient

from helm.api.app import create_app
from helm.risk.circuit import blocks_new_entry
from helm.settings import Settings


def test_manual_band_job(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                helm_data_dir=tmp_path,
                helm_auth_dev=True,
                helm_rate_limit=False,
                helm_admin_emails="a@local",
            )
        )
    )
    client.post("/api/auth/dev", json={"email": "a@local", "admin": True})
    bad = client.post("/api/manual-jobs", json={"symbol": "BTCUSDT", "lower": 100, "upper": 90})
    assert bad.status_code == 400
    created = client.post(
        "/api/manual-jobs",
        json={"symbol": "ethusdt", "lower": 2000, "upper": 2800, "size_usdt": 150, "schedule": "every_15m"},
    )
    assert created.status_code == 200
    assert created.json()["symbol"] == "ETHUSDT"
    jobs = client.get("/api/manual-jobs").json()
    assert len(jobs) == 1


def test_min_equity_blocks_entry() -> None:
    assert blocks_new_entry(80, 100) is True
    assert blocks_new_entry(180, 100) is False
    assert blocks_new_entry(50, 0) is False
