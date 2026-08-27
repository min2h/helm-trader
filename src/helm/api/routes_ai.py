import json

from fastapi import APIRouter, Depends, HTTPException, Request

from helm.actors.control_actor import ControlActor
from helm.ai.autopilot import (
    RawPlan,
    build_autopilot_prompt,
    collect_evidence,
    max_picks,
    plan_jobs,
    render_plan_markdown,
    rule_rank,
    rule_regime,
    validate_plan,
)
from helm.ai.brief import build_analysis_prompt, build_chat_prompt
from helm.ai.client import complete_llm, try_parse_json_block
from helm.ai.news import fetch_headlines
from helm.ai.proposer import apply_proposal, parse_proposal
from helm.ai.reporter import render_daily_report
from helm.api.deps import actor_for, approved_user, current_user, state_of
from helm.auth.limits import limiter
from helm.config.schema import Params
from helm.db.models import User

router = APIRouter()

AI_OFF_MESSAGE = "AI 개입이 꺼져 있어 토큰을 쓰지 않습니다. 설정에서 AI 개입을 켜면 분석이 시작됩니다."


def _user(user: User = Depends(current_user)) -> User:
    return approved_user(user)


def _ai_on(actor: ControlActor) -> Params:
    """Token spend gate. Must run before any key lookup or network call."""
    params = actor.params()
    if params.ai_level == "off":
        raise HTTPException(409, AI_OFF_MESSAGE)
    return params


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
    actor = actor_for(request, user)
    _ai_on(actor)
    text = str(body.get("message") or "").strip()
    if not text:
        raise HTTPException(400, "message required")
    provider, key = _llm(request, user)
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
    actor = actor_for(request, user)
    _ai_on(actor)
    provider, key = _llm(request, user)
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
            proposal = parse_proposal(reply if reply.strip().startswith("{") else json.dumps(payload))
            result = apply_proposal(actor.params(), proposal)
            actor.store.replace(result)
            actor._params = result.params
            applied = [key for key in proposal.param_patches if key not in result.rejected]
        except Exception:
            applied = []
    return {"markdown": markdown, "headlines": headlines, "applied": applied}


@router.get("/ai/news")
def news(request: Request, user: User = Depends(_user)) -> list[dict]:
    if actor_for(request, user).params().ai_level == "off":
        return []
    return fetch_headlines()


def _job_view(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "symbol": row.get("symbol"),
        "schedule": row.get("schedule"),
        "lower": row.get("lower"),
        "upper": row.get("upper"),
        "size_usdt": row.get("size_usdt"),
        "enabled": bool(row.get("enabled")),
        "note": row.get("note") or "",
    }


@router.get("/ai/autopilot")
def autopilot_state(request: Request, user: User = Depends(_user)) -> dict:
    """No tokens spent here, so the UI can always render the current state."""
    state = state_of(request)
    params = actor_for(request, user).params()
    jobs = state.db.list_manual_jobs_by_source(user.id, "ai")
    runs = state.db.list_ai_runs(user.id, limit=5)
    flags = state.db.secret_flags(user.id)
    engine = "ai" if params.ai_level == "params_and_symbols" and flags.get("llm") else "rule"
    return {
        "ai_level": params.ai_level,
        "engine": engine,
        "has_binance": bool(flags.get("binance")),
        "has_llm": bool(flags.get("llm")),
        "allowed": bool(flags.get("binance")),
        "enabled_count": sum(1 for row in jobs if row.get("enabled")),
        "run_state": params.run_state,
        "last_status": params.ai.last_status,
        "last_run_at": params.ai.last_run_at.isoformat() if params.ai.last_run_at else None,
        "size_usdt": params.manual_band.size_usdt,
        "max_picks": max_picks(params),
        "jobs": [_job_view(row) for row in jobs],
        "history": [
            {"id": run["id"], "symbols": run["symbols"], "regime": run["regime"], "at": run["created_at"]}
            for run in runs
        ],
    }


@router.post("/ai/autopilot/run")
@limiter.limit("6/minute")
def autopilot_run(body: dict, request: Request, user: User = Depends(_user)) -> dict:
    state = state_of(request)
    actor = actor_for(request, user)
    params = actor.params()
    if params.run_state == "hard_kill":
        raise HTTPException(409, "하드킬 상태입니다. 포지션을 정리하고 재개한 뒤 다시 실행하세요.")
    secrets = state.db.decrypt_secrets(user.id)
    if not (secrets["binance_key"] and secrets["binance_secret"]):
        raise HTTPException(400, "설정에서 Binance API 키와 시크릿을 먼저 넣으세요. 자동매매는 이 키로 돕니다.")
    use_ai = params.ai_level == "params_and_symbols" and bool(secrets["llm_key"])

    again = bool(body.get("again"))
    exclude = state.db.recent_ai_symbols(user.id, runs=3) if again else []
    try:
        pack = collect_evidence(params, exclude=exclude)
    except Exception as exc:
        raise HTTPException(502, f"시세/지표 수집 실패로 실행하지 않았습니다: {exc}") from exc
    if not pack.candidates:
        actor.mark_ai_run("no_candidate")
        raise HTTPException(409, "거래대금·변동성 검증을 통과한 후보가 없어 실행하지 않았습니다.")

    limit = max_picks(params)
    if use_ai:
        prompt = build_autopilot_prompt(params, pack, picks=limit)
        try:
            reply = complete_llm(
                provider=secrets["llm_provider"] or "anthropic",
                api_key=secrets["llm_key"],
                user_text=prompt,
            )
        except Exception as exc:
            raise HTTPException(502, f"llm error: {exc}") from exc
        plan, accepted, rejected = validate_plan(reply, pack, limit=limit)
    else:
        plan = RawPlan(regime=rule_regime(pack))
        accepted, rejected = rule_rank(params, pack, limit=limit)

    engine = "ai" if use_ai else "rule"
    jobs = plan_jobs(params, accepted)
    markdown = render_plan_markdown(params, pack, plan, jobs, rejected, engine=engine)
    state.db.add_report(user.id, "autopilot", markdown)

    if not jobs:
        actor.mark_ai_run("no_pick")
        state.db.add_ai_run(user.id, symbols=[], regime=plan.regime, detail="no pick")
        return {
            "started": False,
            "engine": engine,
            "reason": "검증을 통과한 추천이 없어 자동매매를 실행하지 않았습니다.",
            "regime": plan.regime,
            "rejected": rejected,
            "warnings": plan.warnings,
            "candidates": [item.symbol for item in pack.candidates],
            "markdown": markdown,
            "jobs": [],
        }

    state.db.delete_manual_jobs(user.id, "ai")
    created = [
        state.db.add_manual_job(
            user.id,
            {
                "symbol": job.symbol,
                "side": "BUY",
                "lower": job.lower,
                "upper": job.upper,
                "schedule": job.schedule,
                "size_usdt": job.size_usdt,
                "enabled": True,
                "source": "ai",
                "note": f"{'AI 확신' if use_ai else '규칙 점수'} {job.confidence} · "
                f"ATR {job.evidence.atr_pct:.2f}% · ADX {job.evidence.adx:.1f} · {job.reason}",
            },
        )
        for job in jobs
    ]
    symbols = [job.symbol for job in jobs]
    state.db.add_ai_run(
        user.id,
        symbols=symbols,
        regime=plan.regime,
        detail=json.dumps({"rejected": rejected, "warnings": plan.warnings}, ensure_ascii=False),
    )
    actor.mark_ai_run(f"{engine}_running", symbols=symbols)
    resumed = True
    if params.run_state == "soft_stop":
        try:
            actor.resume("ai_autopilot")
        except RuntimeError:
            resumed = False
    state.db.audit(user.id, "autopilot_run", f"{engine}:{','.join(symbols)}")
    return {
        "started": True,
        "engine": engine,
        "regime": plan.regime,
        "symbols": symbols,
        "resumed": resumed,
        "rejected": rejected,
        "warnings": plan.warnings,
        "candidates": [item.symbol for item in pack.candidates],
        "markdown": markdown,
        "jobs": [_job_view(row) for row in created],
    }


@router.post("/ai/autopilot/stop")
def autopilot_stop(request: Request, user: User = Depends(_user)) -> dict:
    """Stop needs no AI and no tokens, so it works even after AI is switched off."""
    state = state_of(request)
    actor = actor_for(request, user)
    stopped = state.db.disable_manual_jobs(user.id, "ai")
    params = actor.soft_stop("ai_autopilot_stop")
    actor.mark_ai_run("stopped")
    state.db.audit(user.id, "autopilot_stop", f"jobs={stopped}")
    return {"stopped_jobs": stopped, "run_state": params.run_state}
