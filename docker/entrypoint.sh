#!/bin/sh
set -e

# Bring the database schema up to date, then hand off to the CMD (uvicorn).
echo "fuellog: applying database migrations..."
alembic upgrade head

exec "$@"
