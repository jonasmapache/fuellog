"""Login, logout and language switching."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import (
    current_user, has_users, login_session, logout_session,
    register_failure, register_success, too_many_attempts, verify_password,
)
from ..database import get_db
from ..i18n import LANGUAGES
from ..models import User
from ..security import csrf_protect
from ..templating import render

router = APIRouter(dependencies=[Depends(csrf_protect)])


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


@router.get("/login")
def login_form(request: Request, next: str = "/", db: Session = Depends(get_db)):
    if not has_users(db):
        return RedirectResponse(url="/setup", status_code=303)
    if current_user(request, db):
        return RedirectResponse(url=_safe_next(next), status_code=303)
    return render(request, db, "login.html", next=_safe_next(next), error=None)


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    if not has_users(db):
        return RedirectResponse(url="/setup", status_code=303)

    target = _safe_next(next)
    if too_many_attempts(request):
        return render(request, db, "login.html", next=target, error="login.error", status_code=429)

    user = db.query(User).filter(User.username == username.strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        register_failure(request)
        return render(request, db, "login.html", next=target, error="login.error", status_code=401)

    register_success(request)
    login_session(request, user)
    return RedirectResponse(url=target, status_code=303)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse(url="/login", status_code=303)


@router.post("/lang")
def set_language(request: Request, lang: str = Form(...), next: str = Form("/")):
    if lang in LANGUAGES:
        request.session["lang"] = lang
    return RedirectResponse(url=_safe_next(next), status_code=303)
