from fastapi import APIRouter, Depends, HTTPException, Request

from helm.ai.brief import build_analysis_prompt, build_chat_prompt
from helm.ai.client import complete_llm, try_parse_json_block
from helm.ai.news import fetch_headlines
from helm.ai.proposer import apply_proposal, parse_proposal
from helm.ai.reporter import render_daily_report
from helm.api.deps import actor_for, approved_user, current_user, state_of
from helm.auth.limits import limiter
from helm.db.models import User

router = APIRouter()


def _user(user: User = Depends(current_user)) -> User:
    return approved_user(user)


def _llm(request: Request, user: User) -> tuple[str, str]:
    secrets = state_of(request).db.decrypt_secrets(user.id)
    if not secrets["llm_key"]:
        raise HTTPException(400, "개인 LLM API 키를 설정에서 입력하세요")
    return secrets["llm_provider"] or "anthropic", secrets["llm_key"]


@router.get("/ai/messages")
def messages(request: Request, user: User = Depends(_user)) -> list[dict]:
    return state_of(request).db.list_chat(user.id)


@router.post("/ai/chat")
@limiter.limit("10/minute")
def chat(body: dict, request: Request, user: User = Depends(_user)) -> dict:
    text = str(body.get("message") or "").strip()
    if not text:
        raise HTTPException(400, "message required")
    provider, key = _llm(request, user)
    actor = actor_for(request, user)
    state_of(request).db.add_chat(user.id, "user", text)
    try:
        reply = complete_llm(
            provider=provider,
            api_key=key,
            user_text=build_chat_prompt(actor.params(), text),
        )
    except Exception as exc:
        raise HTTPException(502, f"llm error: {exc}") from exc
    state_of(request).db.add_chat(user.id, "assistant", reply)
    return {"role": "assistant", "content": reply}


@router.post("/ai/analyze")
def analyze(request: Request, user: User = Depends(_user)) -> dict:
    provider, key = _llm(request, user)
    actor = actor_for(request, user)
    user_text, headlines = build_analysis_prompt(actor.params(), actor.status().daily_pnl_pct)
    try:
        reply = complete_llm(provider=provider, api_key=key, user_text=user_text)
    except Exception as exc:
        raise HTTPException(502, f"llm error: {exc}") from exc
    notes = [item["title"] for item in headlines]
    markdown = render_daily_report(
        actor.params(),
        daily_pnl_pct=actor.status().daily_pnl_pct,
        trades=0,
        ai_status="analyzed",
        notes=notes or ["no headlines"],
    )
    markdown += "\n\n## analyst memo\n" + reply
    state_of(request).db.add_report(user.id, "analysis", markdown)
    payload = try_parse_json_block(reply)
    applied = []
    if payload:
        try:
            proposal = parse_proposal(reply if reply.strip().startswith("{") else __import__("json").dumps(payload))
            result = apply_proposal(actor.params(), proposal)
            actor.store.replace(result)
            actor._params = result.params
            applied = [key for key in proposal.param_patches if key not in result.rejected]
        except Exception:
            applied = []
    return {"markdown": markdown, "headlines": headlines, "applied": applied}


@router.get("/ai/news")
def news(_: User = Depends(_user)) -> list[dict]:
    return fetch_headlines()
