from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from helm.api.deps import COOKIE, admin_user, current_user, state_of
from helm.auth.limits import limiter
from helm.auth.oauth import PROVIDERS, oauth_login_url, oauth_profile
from helm.db.models import User
from helm.notify.email import send_email

router = APIRouter()


def _set_session(response: RedirectResponse | object, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=14 * 24 * 3600)


@router.get("/auth/{provider}/login")
@limiter.limit("10/minute")
def login(provider: str, request: Request):
    if provider not in PROVIDERS:
        raise HTTPException(404, "unknown provider")
    state = state_of(request)
    if state.db.is_locked(request.client.host if request.client else "unknown"):
        raise HTTPException(429, "login locked")
    nonce = secrets.token_urlsafe(16)
    try:
        url = oauth_login_url(state.settings, provider, nonce)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    state.db.save_oauth_state(nonce, provider)
    return RedirectResponse(url)


@router.get("/auth/{provider}/callback")
def callback(provider: str, request: Request, code: str = "", state: str = "", error: str = ""):
    app_state = state_of(request)
    ip = request.client.host if request.client else "unknown"
    if error or not code:
        app_state.db.register_failure(ip)
        return RedirectResponse("/?auth=denied")
    saved = app_state.db.pop_oauth_state(state)
    if saved != provider:
        app_state.db.register_failure(ip)
        raise HTTPException(400, "invalid oauth state")
    try:
        profile = oauth_profile(app_state.settings, provider, code)
    except Exception:
        app_state.db.register_failure(ip)
        return RedirectResponse("/?auth=error")
    user = app_state.db.upsert_oauth_user(
        provider=profile.provider,
        subject=profile.subject,
        email=profile.email,
        nickname=profile.nickname,
        admin_emails=app_state.settings.admin_emails,
    )
    app_state.db.clear_failures(ip)
    token = app_state.db.create_session(user.id)
    response = RedirectResponse("/")
    _set_session(response, token)
    return response


@router.post("/auth/dev")
def dev_login(body: dict, request: Request):
    state = state_of(request)
    if not state.settings.helm_auth_dev:
        raise HTTPException(404, "dev login disabled")
    email = str(body.get("email") or "dev@local")
    admin = bool(body.get("admin"))
    emails = set(state.settings.admin_emails)
    if admin:
        emails.add(email.lower())
    user = state.db.upsert_oauth_user(
        provider="dev",
        subject=email,
        email=email,
        nickname=str(body.get("nickname") or email.split("@")[0]),
        admin_emails=emails,
    )
    token = state.db.create_session(user.id)
    from fastapi.responses import JSONResponse

    response = JSONResponse(user.to_public())
    _set_session(response, token)
    return response


@router.post("/auth/logout")
def logout(request: Request):
    token = request.cookies.get(COOKIE, "")
    state_of(request).db.delete_session(token)
    from fastapi.responses import JSONResponse

    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE)
    return response


@router.get("/me")
def me(request: Request, user: User = Depends(current_user)) -> dict:
    payload = user.to_public()
    payload["secrets"] = state_of(request).db.secret_flags(user.id)
    return payload


@router.patch("/me")
def patch_me(body: dict, request: Request, user: User = Depends(current_user)) -> dict:
    updated = state_of(request).db.update_profile(user.id, body)
    actor = state_of(request).hub.for_user(user.id)
    if "min_equity_usdt" in body:
        actor.patch_params({"risk.min_equity_usdt": float(body["min_equity_usdt"])})
    return updated.to_public()


@router.get("/me/secrets")
@limiter.limit("30/minute")
def get_secrets(request: Request, user: User = Depends(current_user)) -> dict:
    if user.status != "approved":
        raise HTTPException(403, "pending approval")
    plain = state_of(request).db.decrypt_secrets(user.id)
    flags = state_of(request).db.secret_flags(user.id)
    return {**flags, **plain}


@router.put("/me/secrets")
def put_secrets(body: dict, request: Request, user: User = Depends(current_user)) -> dict:
    approved = user if user.status == "approved" else None
    if not approved:
        raise HTTPException(403, "pending approval")
    state_of(request).db.put_secrets(
        user.id,
        binance_key=str(body.get("binance_key") or ""),
        binance_secret=str(body.get("binance_secret") or ""),
        llm_provider=str(body.get("llm_provider") or ""),
        llm_key=str(body.get("llm_key") or ""),
    )
    return state_of(request).db.secret_flags(user.id)


@router.get("/admin/users")
def admin_users(request: Request, user: User = Depends(current_user)) -> list[dict]:
    admin_user(user)
    return [item.to_public() for item in state_of(request).db.list_users()]


@router.post("/admin/users/{user_id}/approve")
def approve(user_id: int, request: Request, user: User = Depends(current_user)) -> dict:
    admin_user(user)
    target = state_of(request).db.set_status(user_id, "approved")
    send_email(
        state_of(request).settings,
        target,
        "helm-trader 승인",
        "관리자가 계정을 승인했습니다. 대시보드에 다시 로그인하세요.",
    )
    return target.to_public()


@router.post("/admin/users/{user_id}/suspend")
def suspend(user_id: int, request: Request, user: User = Depends(current_user)) -> dict:
    admin_user(user)
    return state_of(request).db.set_status(user_id, "suspended").to_public()
