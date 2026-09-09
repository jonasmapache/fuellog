"""CSRF protection for state-changing form submissions."""
import secrets

from fastapi import HTTPException, Request

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


async def csrf_protect(request: Request) -> None:
    if request.method in _SAFE_METHODS:
        return
    session_token = request.session.get("csrf")
    try:
        form = await request.form()
    except Exception:  # pragma: no cover - malformed body
        form = {}
    sent = str(form.get("csrf_token") or request.headers.get("x-csrf-token") or "")
    if not session_token or not secrets.compare_digest(sent, session_token):
        raise HTTPException(status_code=403, detail="CSRF check failed")
