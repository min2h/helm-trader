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


PROVIDERS = ("google",)


def _redirect(settings: Settings, provider: str) -> str:
    return f"{settings.helm_public_url.rstrip('/')}/api/auth/{provider}/callback"


def oauth_login_url(settings: Settings, provider: str, state: str) -> str:
    if provider != "google":
        raise ValueError(f"unknown provider {provider}")
    if not settings.google_client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID missing")
    redirect = _redirect(settings, provider)
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


def oauth_profile(settings: Settings, provider: str, code: str) -> OAuthProfile:
    if provider != "google":
        raise ValueError(f"unknown provider {provider}")
    redirect = _redirect(settings, provider)
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
