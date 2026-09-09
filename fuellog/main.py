"""Application factory: middleware, static mounts, routers, error handlers."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .auth import NeedsAdmin, NeedsLogin, NeedsSetup
from .config import APP_VERSION, PHOTOS_DIR, SESSION_HTTPS_ONLY, get_secret_key
from .database import Base, engine
from .routes import routers
from .templating import render

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("fuellog")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Alembic owns the schema in production (run from the entrypoint). This is
    # a safety net for `uvicorn`-only dev runs and brand-new databases.
    Base.metadata.create_all(bind=engine)
    log.info("fuellog %s started", APP_VERSION)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="fuellog", version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=get_secret_key(),
        same_site="lax",
        https_only=SESSION_HTTPS_ONLY,
        max_age=60 * 60 * 24 * 30,
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

    for router in routers:
        app.include_router(router)

    @app.exception_handler(NeedsSetup)
    async def _needs_setup(request: Request, exc: NeedsSetup):
        return RedirectResponse(url="/setup", status_code=303)

    @app.exception_handler(NeedsLogin)
    async def _needs_login(request: Request, exc: NeedsLogin):
        nxt = exc.next_url or "/"
        return RedirectResponse(url=f"/login?next={nxt}", status_code=303)

    @app.exception_handler(NeedsAdmin)
    async def _needs_admin(request: Request, exc: NeedsAdmin):
        from .database import SessionLocal
        db = SessionLocal()
        try:
            return render(request, db, "error.html", status_code=403,
                          title_key="error.403_title", body_key="error.403_body")
        finally:
            db.close()

    @app.exception_handler(404)
    async def _not_found(request: Request, exc):
        from .database import SessionLocal
        db = SessionLocal()
        try:
            return render(request, db, "error.html", status_code=404,
                          title_key="error.404_title", body_key="error.404_body")
        finally:
            db.close()

    return app


app = create_app()
