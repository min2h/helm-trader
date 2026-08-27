from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from helm.settings import Settings


@dataclass(frozen=True)
class OAuthProfile:
    provider: str
    subject: str
    email: str
    nickname: str


PROVIDERS = ("google", "kakao", "naver")


def _redirect(settings: Settings, provider: str) -> str:
    return f"{settings.helm_public_url.rstrip('/')}/api/auth/{provider}/callback"


def oauth_login_url(settings: Settings, provider: str, state: str) -> str:
    redirect = _redirect(settings, provider)
    if provider == "google":
        if not settings.google_client_id:
            raise RuntimeError("GOOGLE_CLIENT_ID missing")
        query = urlencode(
            {
                "client_id": settings.google_client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    if provider == "kakao":
        if not settings.kakao_client_id:
            raise RuntimeError("KAKAO_CLIENT_ID missing")
        query = urlencode(
            {
                "client_id": settings.kakao_client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "state": state,
            }
        )
        return f"https://kauth.kakao.com/oauth/authorize?{query}"
    if provider == "naver":
        if not settings.naver_client_id:
            raise RuntimeError("NAVER_CLIENT_ID missing")
        query = urlencode(
            {
                "client_id": settings.naver_client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "state": state,
            }
        )
        return f"https://nid.naver.com/oauth2.0/authorize?{query}"
    raise ValueError(f"unknown provider {provider}")


def oauth_profile(settings: Settings, provider: str, code: str) -> OAuthProfile:
    redirect = _redirect(settings, provider)
    if provider == "google":
        token = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        token.raise_for_status()
        access = token.json()["access_token"]
        info = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        info.raise_for_status()
        body = info.json()
        return OAuthProfile("google", str(body["id"]), body.get("email", ""), body.get("name", ""))
    if provider == "kakao":
        token = httpx.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.kakao_client_id,
                "client_secret": settings.kakao_client_secret,
                "redirect_uri": redirect,
                "code": code,
            },
            timeout=20,
        )
        token.raise_for_status()
        access = token.json()["access_token"]
        info = httpx.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        info.raise_for_status()
        body = info.json()
        account = body.get("kakao_account") or {}
        profile = account.get("profile") or {}
        return OAuthProfile(
            "kakao",
            str(body["id"]),
            account.get("email") or f"kakao_{body['id']}@users.helm",
            profile.get("nickname") or "",
        )
    if provider == "naver":
        token = httpx.post(
            "https://nid.naver.com/oauth2.0/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.naver_client_id,
                "client_secret": settings.naver_client_secret,
                "redirect_uri": redirect,
                "code": code,
            },
            timeout=20,
        )
        token.raise_for_status()
        access = token.json()["access_token"]
        info = httpx.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        info.raise_for_status()
        resp = info.json().get("response") or {}
        return OAuthProfile(
            "naver",
            str(resp.get("id")),
            resp.get("email") or f"naver_{resp.get('id')}@users.helm",
            resp.get("nickname") or resp.get("name") or "",
        )
    raise ValueError(f"unknown provider {provider}")
