from fastapi import APIRouter, Depends, HTTPException, Request

from helm.api.deps import actor_for, approved_user, current_user
from helm.config.schema import USER_PATCH_FIELDS
from helm.db.models import User

router = APIRouter()


def _user(user: User = Depends(current_user)) -> User:
    return approved_user(user)


@router.get("/params")
def get_params(request: Request, user: User = Depends(_user)) -> dict:
    return actor_for(request, user).params().model_dump(mode="json")


@router.put("/params")
def put_params(patch: dict, request: Request, user: User = Depends(_user)) -> dict:
    unknown = [key for key in patch if key not in USER_PATCH_FIELDS]
    if unknown:
        raise HTTPException(status_code=400, detail={"rejected": unknown})
    try:
        params = actor_for(request, user).patch_params(patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return params.model_dump(mode="json")


@router.get("/symbols")
def get_symbols(request: Request, user: User = Depends(_user)) -> dict:
    return actor_for(request, user).params().symbols.model_dump()


@router.post("/symbols/approve")
def approve_symbol(body: dict, request: Request, user: User = Depends(_user)) -> dict:
    symbol = str(body.get("symbol", "")).upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol required")
    return actor_for(request, user).approve_symbol(symbol).symbols.model_dump()
