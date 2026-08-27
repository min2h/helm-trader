import pytest

from helm.actors.control_actor import ControlActor
from helm.config.store import ParamsStore


def test_soft_and_resume(tmp_path) -> None:
    actor = ControlActor(ParamsStore(tmp_path / "params.json"))
    actor.soft_stop("test")
    assert actor.params().run_state == "soft_stop"
    actor.resume("test")
    assert actor.params().run_state == "running"


def test_hard_kill_requires_fresh_token(tmp_path) -> None:
    actor = ControlActor(ParamsStore(tmp_path / "params.json"))
    token = actor.prepare_hard_kill()["token"]
    with pytest.raises(PermissionError):
        actor.confirm_hard_kill("wrong")
    actor.confirm_hard_kill(token)
    assert actor.params().run_state == "hard_kill"
    kinds = [cmd.kind for cmd in actor.drain_commands()]
    assert "flat_all" in kinds


def test_ai_locked_via_user_radio_only(tmp_path) -> None:
    actor = ControlActor(ParamsStore(tmp_path / "params.json"))
    actor.patch_params({"risk_grade": "aggressive"})
    assert actor.params().risk.leverage == 3
    assert actor.params().risk.per_trade_risk_pct == 2.0
