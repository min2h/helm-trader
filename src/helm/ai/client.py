from __future__ import annotations

import json

import httpx

from helm.ai.prompt import SYSTEM_PROMPT


def complete_llm(*, provider: str, api_key: str, user_text: str, timeout: float = 60.0) -> str:
    if not api_key:
        raise RuntimeError("user LLM key is not configured")
    provider = provider.lower()
    if provider in {"", "off"}:
        raise RuntimeError("choose anthropic or openai in settings")
    if provider == "anthropic":
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1600,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_text}],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json().get("content") or []
        return "".join(block.get("text", "") for block in content if block.get("type") == "text")
    if provider == "openai":
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4.1-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"unsupported llm provider: {provider}")


def try_parse_json_block(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
