# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] - 2026-09-09

### Fixed
- Range ("range on a full tank") stayed blank after a CSV import because the
  imported vehicles had no tank capacity. The range now falls back to the
  largest full-tank fill-up on record (shown with a `~` prefix), and the CSV
  importer sets a rough tank-size estimate on vehicles it creates.

### Added
- Time zone is now a searchable dropdown of IANA zones in Settings instead of a
  free-text field (`tzdata` is bundled so the list is complete on any host).

## [0.1.1] - 2026-09-09

### Fixed
- `PermissionError` on a fresh `/data` bind mount that Docker created as
  `root:root`. The container now starts as root, chowns `/data` (recursively,
  only when needed) and re-maps its app user to `PUID`/`PGID`, then drops to
  that non-root user via `gosu` before running migrations and the app. Works
  for new and existing data directories, and is skipped when the container is
  started with an explicit `--user`.

### Added
- `PUID` / `PGID` environment variables (default `1000` / `1000`; Unraid `99` /
  `100`) and matching entries in the compose file and Unraid template.

## [0.1.0]

### Added
- First public release of fuellog, rebuilt from a private prototype.
- First-run setup wizard creating a bcrypt/argon2-hashed admin account;
  additional users manageable from Settings.
- English and German UI, configurable currency, light/dark mode.
- CSV import and export.
- Odometer-only entries.
- Prebuilt multi-arch image published to `ghcr.io/jonasmapache/fuellog`,
  Docker Compose file and an Unraid Community Applications template.
- Alembic-managed schema; auto-generated and persisted `SECRET_KEY`;
  `/healthz` endpoint; CSRF protection on all forms.
