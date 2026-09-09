"""Minimal dictionary-based translations (no gettext / build step).

Add a language by dropping ``fuellog/i18n/<code>.py`` with a ``TRANSLATIONS``
dict and registering it in ``LANGUAGES`` / ``_TABLES`` below.
"""
import logging

from .de import TRANSLATIONS as _DE
from .en import TRANSLATIONS as _EN

log = logging.getLogger(__name__)

LANGUAGES = {"en": "English", "de": "Deutsch"}
_TABLES = {"en": _EN, "de": _DE}


def translate(lang: str, key: str, **kwargs) -> str:
    table = _TABLES.get(lang, _EN)
    text = table.get(key)
    if text is None and lang != "en":
        text = _EN.get(key)
    if text is None:
        log.warning("missing translation key: %s", key)
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def resolve_language(request, settings_lang: str | None) -> str:
    """session override > instance default > Accept-Language > English."""
    session_lang = None
    try:
        session_lang = request.session.get("lang")
    except (AssertionError, AttributeError):
        pass
    if session_lang in _TABLES:
        return session_lang
    if settings_lang in _TABLES:
        return settings_lang
    accept = request.headers.get("accept-language", "")
    for part in accept.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in _TABLES:
            return code
    return "en"
