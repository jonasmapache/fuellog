"""Password hashing, session helpers and route guards.

Guards are FastAPI dependencies that raise lightweight exceptions; the app
registers handlers (see ``main.py``) that turn those into redirects or a
403 page.
"""
import time
from collections import defaultdict

from fastapi import Depends, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

_hasher = PasswordHash.recommended()

# --- passwords ---

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except (ValueError, TypeError):
        return False


# --- brute-force throttle (per client IP, in memory) ---

_FAILURES: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 300
_MAX_FAILURES = 8


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def too_many_attempts(request: Request) -> bool:
    now = time.time()
    ip = _client_ip(request)
    recent = [t for t in _FAILURES[ip] if now - t < _WINDOW_SECONDS]
    _FAILURES[ip] = recent
    return len(recent) >= _MAX_FAILURES


def register_failure(request: Request) -> None:
    _FAILURES[_client_ip(request)].append(time.time())


def register_success(request: Request) -> None:
    _FAILURES.pop(_client_ip(request), None)


# --- session ---

def login_session(request: Request, user: User) -> None:
    request.session["uid"] = user.id


def logout_session(request: Request) -> None:
    request.session.pop("uid", None)


def has_users(db: Session) -> bool:
    return db.query(User.id).first() is not None


def current_user(request: Request, db: Session) -> User | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    return db.get(User, uid)


# --- guard exceptions ---

class NeedsSetup(Exception):
    pass


class NeedsLogin(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


class NeedsAdmin(Exception):
    pass


# --- guard dependencies ---

def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    if not has_users(db):
        raise NeedsSetup()
    user = current_user(request, db)
    if user is None:
        raise NeedsLogin(request.url.path)
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise NeedsAdmin()
    return user
