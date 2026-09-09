"""First-run wizard: create the initial administrator account."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import has_users, hash_password, login_session
from ..database import get_db
from ..models import User
from ..security import csrf_protect
from ..templating import render

router = APIRouter(dependencies=[Depends(csrf_protect)])


@router.get("/setup")
def setup_form(request: Request, db: Session = Depends(get_db)):
    if has_users(db):
        return RedirectResponse(url="/", status_code=303)
    return render(request, db, "setup.html", error=None)


@router.post("/setup")
def setup_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if has_users(db):
        return RedirectResponse(url="/", status_code=303)

    username = username.strip()
    error = None
    if not username:
        error = "setup.error_username"
    elif len(password) < 8:
        error = "setup.error_short"
    elif password != password_confirm:
        error = "setup.error_mismatch"

    if error:
        return render(request, db, "setup.html", error=error, status_code=400)

    user = User(username=username, password_hash=hash_password(password), is_admin=True)
    db.add(user)
    db.commit()
    login_session(request, user)
    return RedirectResponse(url="/", status_code=303)
