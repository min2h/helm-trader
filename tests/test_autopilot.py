import json

from fastapi.testclient import TestClient

from helm.ai.autopilot import Evidence, EvidencePack, plan_jobs, rule_rank, validate_plan
from helm.api.app import create_app
from helm.config.schema import Params
from helm.settings import Settings


def _evidence(symbol: str, last: float = 100.0, atr_value: float = 2.0) -> Evidence:
    return Evidence(
        symbol=symbol,
        last=last,
        change_pct=1.5,
        quote_volume=500_000_000.0,
        atr=atr_value,
        atr_pct=atr_value / last * 100,
        adx=28.0,
        range_high=last * 1.05,
        range_low=last * 0.95,
        funding_apr=12.0,
        bars=240,
        timeframe="15m",
    )


def _pack(*symbols: str) -> EvidencePack:
    return EvidencePack(
        timeframe="15m",
        market="futures",
        candidates=[_evidence(symbol) for symbol in symbols],
    )


def test_symbols_outside_the_verified_table_are_dropped() -> None:
    pack = _pack("BTCUSDT", "ETHUSDT")
    reply = json.dumps(
        {
            "regime": "trend",
            "picks": [
                {"symbol": "MOONUSDT", "schedule": "every_15m", "confidence": 0.9, "reason": "상장 예정 루머라서"},
                {"symbol": "BTCUSDT", "schedule": "every_15m", "confidence": 0.8, "reason": "ADX 28로 추세 유지"},
            ],
        }
    )
    _, accepted, rejected = validate_plan(reply, pack, limit=3)
    assert [item[0].symbol for item in accepted] == ["BTCUSDT"]
    assert any("MOONUSDT" in note for note in rejected)


def test_low_confidence_and_missing_reason_are_dropped() -> None:
    pack = _pack("BTCUSDT", "ETHUSDT")
    reply = json.dumps(
        {
            "picks": [
                {"symbol": "BTCUSDT", "schedule": "every_1h", "confidence": 0.3, "reason": "ADX 28로 추세 유지"},
                {"symbol": "ETHUSDT", "schedule": "every_1h", "confidence": 0.9, "reason": "감"},
            ]
        }
    )
    _, accepted, rejected = validate_plan(reply, pack, limit=3)
    assert accepted == []
    assert len(rejected) == 2


def test_unknown_schedule_falls_back_to_timeframe_default() -> None:
    pack = _pack("BTCUSDT")
    reply = json.dumps(
        {"picks": [{"symbol": "BTCUSDT", "schedule": "매분", "confidence": 0.8, "reason": "ADX 28로 추세 유지"}]}
    )
    _, accepted, _ = validate_plan(reply, pack, limit=3)
    assert accepted[0][0].schedule == "every_15m"


def test_limit_follows_concurrent_position_cap() -> None:
    pack = _pack("AUSDT", "BUSDT", "CUSDT")
    reply = json.dumps(
        {
            "picks": [
                {"symbol": s, "schedule": "every_1h", "confidence": 0.8, "reason": "거래대금 500M으로 충분"}
                for s in ("AUSDT", "BUSDT", "CUSDT")
            ]
        }
    )
    _, accepted, rejected = validate_plan(reply, pack, limit=1)
    assert len(accepted) == 1
    assert any("한도" in note for note in rejected)


def test_bands_come_from_atr_not_from_the_model() -> None:
    params = Params(updated_by="user")
    params.strategy.trend.atr_stop_mult = 2.0
    params.manual_band.size_usdt = 250.0
    pack = _pack("BTCUSDT")
    reply = json.dumps(
        {"picks": [{"symbol": "BTCUSDT", "schedule": "every_15m", "confidence": 0.8, "reason": "ADX 28로 추세 유지"}]}
    )
    _, accepted, _ = validate_plan(reply, pack, limit=3)
    jobs = plan_jobs(params, accepted)
    assert len(jobs) == 1
    assert jobs[0].lower == 96.0
    assert jobs[0].upper == 108.0
    assert jobs[0].size_usdt == 250.0


def test_rule_engine_ranks_without_any_llm() -> None:
    params = Params(updated_by="user")
    params.strategy_mode = "trend"
    pack = EvidencePack(
        timeframe="15m",
        market="futures",
        candidates=[
            Evidence(
                symbol="TRENDUSDT",
                last=100.0,
                change_pct=3.0,
                quote_volume=900_000_000.0,
                atr=3.0,
                atr_pct=3.0,
                adx=38.0,
                range_high=108.0,
                range_low=96.0,
                funding_apr=8.0,
                bars=240,
                timeframe="15m",
            ),
            Evidence(
                symbol="FLATUSDT",
                last=10.0,
                change_pct=0.1,
                quote_volume=25_000_000.0,
                atr=0.02,
                atr_pct=0.2,
                adx=8.0,
                range_high=10.1,
                range_low=9.9,
                funding_apr=1.0,
                bars=240,
                timeframe="15m",
            ),
        ],
    )
    accepted, rejected = rule_rank(params, pack, limit=1)
    assert [item[0].symbol for item in accepted] == ["TRENDUSDT"]
    assert accepted[0][0].schedule == "every_15m"
    assert "ADX" in accepted[0][0].reason
    assert rejected


def test_rule_engine_prefers_flat_names_in_grid_mode() -> None:
    params = Params(updated_by="user")
    params.strategy_mode = "grid"
    pack = EvidencePack(
        timeframe="15m",
        market="futures",
        candidates=[
            Evidence("TRENDUSDT", 100.0, 3.0, 500_000_000.0, 3.0, 3.0, 38.0, 108.0, 96.0, 8.0, 240, "15m"),
            Evidence("RANGEUSDT", 100.0, 0.2, 500_000_000.0, 2.0, 2.0, 9.0, 104.0, 96.0, 1.0, 240, "15m"),
        ],
    )
    accepted, _ = rule_rank(params, pack, limit=1)
    assert accepted[0][0].symbol == "RANGEUSDT"


def test_garbage_reply_starts_nothing() -> None:
    _, accepted, rejected = validate_plan("죄송하지만 JSON을 못 만들겠습니다", _pack("BTCUSDT"), limit=3)
    assert accepted == []
    assert rejected


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
    client.put("/api/params", json={"ai_level": "params_and_symbols"})
    return client


def _fake_llm(symbol: str):
    def inner(**_kwargs):
        return json.dumps(
            {
                "regime": "trend",
                "picks": [
                    {
                        "symbol": symbol,
                        "schedule": "every_1h",
                        "confidence": 0.82,
                        "reason": "ADX 28, 거래대금 500M으로 슬리피지 여유",
                    }
                ],
                "warnings": ["펀딩 12% APR은 롱 캐리를 깎는다"],
            }
        )

    return inner


def test_run_creates_ai_jobs_then_stop_disables_them(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    monkeypatch.setattr("helm.api.routes_ai.collect_evidence", lambda *_a, **_k: _pack("BTCUSDT", "ETHUSDT"))
    monkeypatch.setattr("helm.api.routes_ai.complete_llm", _fake_llm("BTCUSDT"))

    run = client.post("/api/ai/autopilot/run", json={})
    assert run.status_code == 200
    body = run.json()
    assert body["started"] is True
    assert body["symbols"] == ["BTCUSDT"]
    assert client.get("/api/params").json()["symbols"]["active"] == ["BTCUSDT"]

    jobs = client.get("/api/manual-jobs").json()
    assert [job["source"] for job in jobs] == ["ai"]
    assert jobs[0]["lower"] == 96.0

    state = client.get("/api/ai/autopilot").json()
    assert state["enabled_count"] == 1

    stopped = client.post("/api/ai/autopilot/stop")
    assert stopped.json() == {"stopped_jobs": 1, "run_state": "soft_stop"}
    assert client.get("/api/ai/autopilot").json()["enabled_count"] == 0


def test_reanalyze_excludes_the_previous_picks(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    seen: list[list[str]] = []

    def fake_evidence(_params, *, exclude=None, **_k):
        seen.append(sorted(exclude or []))
        remaining = [s for s in ("BTCUSDT", "ETHUSDT") if s not in (exclude or [])]
        return _pack(*remaining)

    monkeypatch.setattr("helm.api.routes_ai.collect_evidence", fake_evidence)
    monkeypatch.setattr("helm.api.routes_ai.complete_llm", _fake_llm("BTCUSDT"))
    client.post("/api/ai/autopilot/run", json={})

    monkeypatch.setattr("helm.api.routes_ai.complete_llm", _fake_llm("ETHUSDT"))
    again = client.post("/api/ai/autopilot/run", json={"again": True})
    assert seen[-1] == ["BTCUSDT"]
    assert again.json()["symbols"] == ["ETHUSDT"]
    jobs = client.get("/api/manual-jobs").json()
    assert [job["symbol"] for job in jobs] == ["ETHUSDT"]


def test_run_does_nothing_when_every_pick_fails_validation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    monkeypatch.setattr("helm.api.routes_ai.collect_evidence", lambda *_a, **_k: _pack("BTCUSDT"))
    monkeypatch.setattr("helm.api.routes_ai.complete_llm", _fake_llm("SCAMUSDT"))
    body = client.post("/api/ai/autopilot/run", json={}).json()
    assert body["started"] is False
    assert client.get("/api/manual-jobs").json() == []
