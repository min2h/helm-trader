from fastapi import Cookie, HTTPException, Request

from helm.actors.control_actor import ControlActor
from helm.actors.hub import ActorHub
from helm.db.models import User
from helm.db.store import Database
from helm.settings import Settings

COOKIE = "helm_session"


class AppState:
    def __init__(self, settings: Settings, db: Database, hub: ActorHub) -> None:
        self.settings = settings
        self.db = db
        self.hub = hub


def state_of(request: Request) -> AppState:
    return request.app.state.helm


def current_user(request: Request, helm_session: str | None = Cookie(default=None)) -> User:
    user = state_of(request).db.user_for_session(helm_session or "")
    if not user:
        raise HTTPException(status_code=401, detail="login required")
    return user


def approved_user(user: User) -> User:
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="account suspended")
    if user.status != "approved":
        raise HTTPException(status_code=403, detail="pending approval")
    return user


def admin_user(user: User) -> User:
    approved_user(user)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return user


def actor_for(request: Request, user: User) -> ControlActor:
    return state_of(request).hub.for_user(user.id)
