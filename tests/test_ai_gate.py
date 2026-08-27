from fastapi.testclient import TestClient

from helm.ai.autopilot import Evidence, EvidencePack
from helm.api.app import create_app
from helm.settings import Settings


def _pack() -> EvidencePack:
    item = Evidence(
        symbol="BTCUSDT",
        last=100.0,
        change_pct=1.0,
        quote_volume=900_000_000.0,
        atr=2.0,
        atr_pct=2.0,
        adx=30.0,
        range_high=105.0,
        range_low=95.0,
        funding_apr=10.0,
        bars=240,
        timeframe="15m",
    )
    return EvidencePack(timeframe="15m", market="futures", candidates=[item])


def _client(tmp_path):
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_catalog_warm=False,
        helm_admin_emails="admin@local",
        helm_master_key="",
    )
    client = TestClient(create_app(settings))
    client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    client.put(
        "/api/me/secrets",
        json={
            "llm_provider": "anthropic",
            "llm_key": "sk-test",
            "binance_key": "bn-key",
            "binance_secret": "bn-secret",
        },
    )
    return client


def _no_tokens(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise AssertionError("LLM must not be called while AI is off")

    for target in (
        "helm.api.routes_ai.complete_llm",
        "helm.api.routes_ai.build_analysis_prompt",
        "helm.api.routes_ai.collect_evidence",
        "helm.api.routes_ai.fetch_headlines",
    ):
        monkeypatch.setattr(target, boom)


def test_ai_off_spends_no_tokens(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    _no_tokens(monkeypatch)
    client.put("/api/params", json={"ai_level": "off"})

    chat = client.post("/api/ai/chat", json={"message": "지금 사도 되나?"})
    assert chat.status_code == 409
    analyze = client.post("/api/ai/analyze")
    assert analyze.status_code == 409
    assert client.get("/api/ai/news").json() == []
    state = client.get("/api/ai/autopilot").json()
    assert state["engine"] == "rule"
    assert state["allowed"] is True


def test_off_blocks_chat_before_history_is_written(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    _no_tokens(monkeypatch)
    client.put("/api/params", json={"ai_level": "off"})
    client.post("/api/ai/chat", json={"message": "기록되면 안 됨"})
    assert client.get("/api/ai/messages").json() == []


def test_autopilot_without_symbol_level_ai_uses_the_rule_engine(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    monkeypatch.setattr("helm.api.routes_ai.collect_evidence", lambda *_a, **_k: _pack())

    def boom(**_k):
        raise AssertionError("LLM must not be called unless AI picks symbols")

    monkeypatch.setattr("helm.api.routes_ai.complete_llm", boom)
    for level in ("off", "params_only"):
        client.put("/api/params", json={"ai_level": level})
        body = client.post("/api/ai/autopilot/run", json={}).json()
        assert body["engine"] == "rule"
        assert body["started"] is True


def test_autopilot_requires_binance_keys(tmp_path, monkeypatch) -> None:
    settings = Settings(
        helm_data_dir=tmp_path,
        helm_auth_dev=True,
        helm_rate_limit=False,
        helm_catalog_warm=False,
        helm_admin_emails="admin@local",
        helm_master_key="",
    )
    client = TestClient(create_app(settings))
    client.post("/api/auth/dev", json={"email": "admin@local", "admin": True})
    _no_tokens(monkeypatch)
    run = client.post("/api/ai/autopilot/run", json={})
    assert run.status_code == 400
    assert "Binance" in run.json()["detail"]
    assert client.get("/api/ai/autopilot").json()["has_binance"] is False


def test_stop_works_without_ai_or_tokens(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    _no_tokens(monkeypatch)
    client.put("/api/params", json={"ai_level": "off"})
    stopped = client.post("/api/ai/autopilot/stop")
    assert stopped.status_code == 200
    assert stopped.json()["run_state"] == "soft_stop"
