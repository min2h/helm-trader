from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from helm.config.schema import ClampResult, Params, merge_ai_patches

ALLOWED_REGIMES = {"trend", "range", "high_vol_chop", "funding_rich"}


class AiProposal(BaseModel):
    regime: str = "trend"
    param_patches: dict[str, Any] = Field(default_factory=dict)
    symbol_ranks: list[str] = Field(default_factory=list)
    report_md: str = ""
    warnings: list[str] = Field(default_factory=list)


def parse_proposal(raw: str) -> AiProposal:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("proposal is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("proposal must be a JSON object")
    proposal = AiProposal.model_validate(payload)
    if proposal.regime not in ALLOWED_REGIMES:
        raise ValueError(f"unknown regime: {proposal.regime}")
    return proposal


def apply_proposal(current: Params, proposal: AiProposal) -> ClampResult:
    patches = dict(proposal.param_patches)
    if proposal.symbol_ranks:
        patches["symbols.pending_approval"] = [s.upper() for s in proposal.symbol_ranks]
    result = merge_ai_patches(current, patches)
    result.params.ai.last_run_at = datetime.now(timezone.utc)
    result.params.ai.last_status = "applied" if not result.rejected else "partial"
    return result


def safe_parse(raw: str) -> AiProposal | None:
    try:
        return parse_proposal(raw)
    except (ValueError, ValidationError):
        return None
