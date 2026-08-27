import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from helm.ai.reporter import render_daily_report
from helm.api.deps import actor_for, approved_user, current_user, state_of
from helm.api.sse import status_payload
from helm.auth.limits import limiter
from helm.db.models import User
from helm.research.data import fetch_klines
from helm.risk.circuit import blocks_new_entry

router = APIRouter()


def _user(user: User = Depends(current_user)) -> User:
    return approved_user(user)


@router.get("/status")
def status(request: Request, user: User = Depends(_user)) -> dict:
    actor = actor_for(request, user)
    payload = status_payload(actor)
    payload["nickname"] = user.nickname
    payload["min_equity_usdt"] = user.min_equity_usdt
    payload["entry_blocked"] = blocks_new_entry(0, user.min_equity_usdt) and user.min_equity_usdt > 0
    payload["jobs"] = state_of(request).db.list_manual_jobs(user.id)
    return payload


@router.get("/sse/status")
async def sse_status(request: Request, user: User = Depends(_user)):
    actor = actor_for(request, user)

    async def events():
        while True:
            if await request.is_disconnected():
                break
            yield {"event": "status", "data": json.dumps(status_payload(actor), default=str)}
            await asyncio.sleep(2)

    return EventSourceResponse(events())


@router.get("/reports/latest")
def latest_report(request: Request, user: User = Depends(_user)) -> dict:
    stored = state_of(request).db.latest_report(user.id)
    if stored:
        return {"path": stored.get("id"), "kind": stored.get("kind"), "markdown": stored["markdown"]}
    actor = actor_for(request, user)
    runtime = actor.status()
    return {
        "path": None,
        "kind": "daily",
        "markdown": render_daily_report(
            actor.params(),
            daily_pnl_pct=runtime.daily_pnl_pct,
            trades=0,
            ai_status=actor.params().ai.last_status,
            notes=["no batch report yet; rule engine keeps last params"],
        ),
    }


@router.get("/reports")
def list_kind(request: Request, user: User = Depends(_user), kind: str | None = None) -> dict:
    stored = state_of(request).db.latest_report(user.id, kind)
    return stored or {"markdown": ""}


@router.get("/manual-jobs")
def list_jobs(request: Request, user: User = Depends(_user)) -> list[dict]:
    return state_of(request).db.list_manual_jobs(user.id)


@router.post("/manual-jobs")
@limiter.limit("30/minute")
def create_job(body: dict, request: Request, user: User = Depends(_user)) -> dict:
    if float(body.get("lower") or 0) >= float(body.get("upper") or 0):
        raise HTTPException(400, "lower must be below upper")
    return state_of(request).db.add_manual_job(user.id, body)


@router.post("/manual-jobs/{job_id}/toggle")
def toggle_job(job_id: int, body: dict, request: Request, user: User = Depends(_user)) -> dict:
    return state_of(request).db.set_manual_enabled(user.id, job_id, bool(body.get("enabled", True)))


@router.delete("/manual-jobs/{job_id}")
def delete_job(job_id: int, request: Request, user: User = Depends(_user)) -> dict:
    state_of(request).db.delete_manual_job(user.id, job_id)
    return {"ok": True}


@router.get("/market/klines")
def klines(symbol: str = "BTCUSDT", interval: str = "15m", market: str = "futures") -> dict:
    frame = fetch_klines(symbol, interval, limit=300, market=market)
    records = []
    for rec in frame.to_dict(orient="records"):
        records.append(
            {
                "time": int(rec["open_time"].timestamp()),
                "open": float(rec["open"]),
                "high": float(rec["high"]),
                "low": float(rec["low"]),
                "close": float(rec["close"]),
            }
        )
    return {"symbol": symbol.upper(), "interval": interval, "bars": records}
