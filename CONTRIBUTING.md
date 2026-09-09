# Contributing

Thanks for your interest in fuellog.

## Getting set up

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=$PWD/.devdata
alembic upgrade head
uvicorn fuellog.main:app --reload
```

## Guidelines

- Keep it small and dependency-light. The whole point is a container that's
  quick to run and easy to reason about.
- Server-rendered Jinja templates, vanilla JS, no front-end build step.
- Third-party JS/CSS is vendored under `fuellog/static/vendor/` – don't add CDN
  links.
- Schema changes: edit `fuellog/models.py`, then
  `alembic revision --autogenerate -m "..."` and review the generated migration.
- New UI strings go through `t('some.key')` and must be added to **both**
  `fuellog/i18n/en.py` and `fuellog/i18n/de.py`. A new language is a new file in
  `fuellog/i18n/` registered in `fuellog/i18n/__init__.py`.
- State-changing routes must include the CSRF token field and go through the
  `csrf_protect` dependency (add it to the router).

## Pull requests

Describe the change and how you tested it. Screenshots for UI changes are
appreciated.
