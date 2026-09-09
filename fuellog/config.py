"""Runtime configuration derived from environment variables.

Everything here is optional: the app runs with sane defaults and no env vars
at all. Persistent state (database, uploaded photos, generated secret key)
lives under ``DATA_DIR`` so a single bind-mount is a complete backup.
"""
import os
import secrets
from pathlib import Path

from . import __version__

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "fuellog.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

PHOTOS_DIR = DATA_DIR / "vehicle_photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY_FILE = DATA_DIR / "secret_key"

# Shown in the UI footer and used to bust static-asset caches after an update.
APP_VERSION = os.environ.get("APP_VERSION") or __version__

# Fallback UI language before any AppSettings row exists (first run).
DEFAULT_LANGUAGE = (os.environ.get("APP_DEFAULT_LANG") or "en").lower()

# Marks the session cookie Secure. Leave off if you terminate TLS elsewhere
# but still want the app reachable over plain HTTP on the LAN.
SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "").lower() in {"1", "true", "yes"}

MAX_PHOTO_BYTES = int(os.environ.get("MAX_PHOTO_BYTES", 5 * 1024 * 1024))


def get_secret_key() -> str:
    """Return the session-signing key.

    Priority: ``SECRET_KEY`` env var > previously persisted key > freshly
    generated key (written to ``DATA_DIR/secret_key`` so sessions survive
    restarts without the user having to manage a secret).
    """
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    if SECRET_KEY_FILE.exists():
        stored = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    key = secrets.token_urlsafe(48)
    SECRET_KEY_FILE.write_text(key, encoding="utf-8")
    try:
        SECRET_KEY_FILE.chmod(0o600)
    except OSError:
        pass  # e.g. on filesystems that don't support chmod
    return key
