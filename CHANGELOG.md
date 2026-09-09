# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
