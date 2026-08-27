from fastapi import APIRouter, Depends, HTTPException, Request

from helm.api.deps import actor_for, approved_user, current_user, state_of
from helm.db.models import User

router = APIRouter()


def _user(user: User = Depends(current_user)) -> User:
    return approved_user(user)


@router.post("/control/soft-stop")
def soft_stop(request: Request, user: User = Depends(_user)) -> dict:
    state_of(request).db.audit(user.id, "soft_stop", "api")
    return actor_for(request, user).soft_stop("api").model_dump(mode="json")


@router.post("/control/resume")
def resume(request: Request, user: User = Depends(_user)) -> dict:
    try:
        return actor_for(request, user).resume("api").model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/control/hard-kill/prepare")
def prepare(request: Request, user: User = Depends(_user)) -> dict:
    return actor_for(request, user).prepare_hard_kill()


@router.post("/control/hard-kill/confirm")
def confirm(body: dict, request: Request, user: User = Depends(_user)) -> dict:
    token = str(body.get("token", ""))
    try:
        params = actor_for(request, user).confirm_hard_kill(token, "api")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    state_of(request).db.audit(user.id, "hard_kill", "api")
    return params.model_dump(mode="json")
