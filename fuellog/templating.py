"""Jinja2 setup and a ``render`` helper that injects the common context
(current user, settings snapshot, translator, money formatter, icons,
CSRF token, map config, theme)."""
import secrets
from pathlib import Path

from fastapi import Request
from markupsafe import Markup
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from .config import APP_VERSION
from .i18n import LANGUAGES, resolve_language, translate
from .icons import icon as _icon
from .money import format_money
from .settings_service import get_settings

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
templates.env.globals["icon"] = lambda name, cls="": Markup(_icon(name, cls))
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["languages"] = LANGUAGES


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def flash_text(request: Request, db: Session, key: str, **kwargs) -> str:
    """Translate a message key in the current request's language (for
    one-off notices built inside route handlers)."""
    settings = get_settings(db)
    lang = resolve_language(request, settings.default_language)
    return translate(lang, key, **kwargs)


def render(request: Request, db: Session, name: str, *, user=None, status_code: int = 200, **ctx):
    settings = get_settings(db)
    lang = resolve_language(request, settings.default_language)
    theme = request.cookies.get("theme", "system")

    ctx.update(
        request=request,
        current_user=user,
        settings=settings,
        lang=lang,
        theme=theme,
        csrf_token=csrf_token(request),
        t=lambda key, **kw: translate(lang, key, **kw),
        money=lambda value, **kw: format_money(value, settings, **kw),
        map_config={
            "enabled": settings.geocoding_enabled,
            "tile_url": settings.tile_url,
            "tile_attribution": settings.tile_attribution,
        },
    )
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
