from helm.ai.brief import build_chat_prompt
from helm.ai.prompt import SYSTEM_PROMPT
from helm.config.schema import Params


def test_system_prompt_forbids_execution() -> None:
    assert "주문" in SYSTEM_PROMPT or "place" in SYSTEM_PROMPT.lower()
    assert "leverage" in SYSTEM_PROMPT.lower() or "레버리지" in SYSTEM_PROMPT
    assert "param_patches" in SYSTEM_PROMPT


def test_chat_prompt_keeps_user_question() -> None:
    text = build_chat_prompt(Params(), "레버리지 20배로 올려줘")
    assert "레버리지 20배" in text
    assert "run_state" in text
