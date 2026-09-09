#!/bin/sh
# Fix ownership of the (possibly host-created) /data bind mount, then drop from
# root to the unprivileged app user before running migrations and the app.
#
# Works for freshly created and pre-existing data directories, and regardless
# of who owns the mount initially (root, another uid, ...). If the container is
# started with an explicit non-root --user, the ownership step is skipped and
# the app runs directly as that user.
set -e

APP_USER=appuser
APP_GROUP=appuser
DATA_DIR="${DATA_DIR:-/data}"

run_app() {
    echo "fuellog: applying database migrations..."
    alembic upgrade head
    exec "$@"
}

if [ "$(id -u)" != "0" ]; then
    # Started with an explicit non-root --user; nothing to fix, just run.
    run_app "$@"
fi

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Re-map the app user/group to the requested ids (idempotent).
if [ "$(id -g "$APP_GROUP" 2>/dev/null)" != "$PGID" ]; then
    groupmod -o -g "$PGID" "$APP_GROUP"
fi
if [ "$(id -u "$APP_USER" 2>/dev/null)" != "$PUID" ]; then
    usermod -o -u "$PUID" -g "$PGID" "$APP_USER"
fi

mkdir -p "$DATA_DIR"
# Only chown when needed - avoids a slow recursive pass on every restart once
# ownership is already correct.
current_owner="$(stat -c '%u:%g' "$DATA_DIR" 2>/dev/null || echo '')"
if [ "$current_owner" != "${PUID}:${PGID}" ]; then
    echo "fuellog: fixing ownership of $DATA_DIR -> ${PUID}:${PGID}"
    chown -R "${PUID}:${PGID}" "$DATA_DIR" || \
        echo "fuellog: WARNING could not chown $DATA_DIR (read-only or root-squashed mount?)"
fi

echo "fuellog: running as UID ${PUID} / GID ${PGID}"
if [ "$PUID" = "0" ]; then
    # Explicitly asked to stay root.
    run_app "$@"
fi

exec gosu "${PUID}:${PGID}" "$0" "$@"
