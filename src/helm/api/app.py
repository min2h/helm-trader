from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from helm.auth.limits import limiter

from helm.actors.hub import ActorHub
from helm.api.deps import AppState
from helm.api.routes_ai import router as ai_router
from helm.api.routes_auth import router as auth_router
from helm.api.routes_control import router as control_router
from helm.api.routes_params import router as params_router
from helm.api.routes_status import router as status_router
from helm.auth.crypto import SecretBox
from helm.db.store import Database
from helm.research.http import use_system_certs
from helm.settings import Settings, get_settings


class BodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = 256_000) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > self.max_bytes:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "payload too large"}, status_code=413)
        return await call_next(request)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    use_system_certs()
    settings.helm_data_dir.mkdir(parents=True, exist_ok=True)
    box = SecretBox(settings.helm_master_key, settings.helm_data_dir / ".master_key")
    db = Database(settings.db_path, box)
    hub = ActorHub(settings.helm_data_dir)
    state = AppState(settings, db, hub)

    app = FastAPI(title="helm-trader", version="0.2.0")
    app.state.helm = state
    app.state.limiter = limiter
    limiter.enabled = settings.helm_rate_limit
    if settings.helm_rate_limit:
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["http://127.0.0.1:5173"],
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(params_router, prefix="/api")
    app.include_router(control_router, prefix="/api")
    app.include_router(status_router, prefix="/api")
    app.include_router(ai_router, prefix="/api")

    web_dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.on_event("shutdown")
    def shutdown() -> None:
        db.close()

    return app
