import pytest

from helm.ai.proposer import apply_proposal, parse_proposal
from helm.config.schema import Params


def test_parse_rejects_non_json() -> None:
    with pytest.raises(ValueError):
        parse_proposal("please raise leverage to 20")


def test_apply_clamps_and_keeps_engine_runnable() -> None:
    proposal = parse_proposal(
        """
        {
          "regime": "trend",
          "param_patches": {
            "strategy.trend.donchian_n": 99,
            "run_state": "hard_kill"
          },
          "symbol_ranks": ["solusdt"],
          "report_md": "ok",
          "warnings": []
        }
        """
    )
    result = apply_proposal(Params(), proposal)
    assert result.params.strategy.trend.donchian_n == 60
    assert result.params.run_state == "running"
    assert "SOLUSDT" in result.params.symbols.pending_approval
