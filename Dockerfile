FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    PUID=1000 \
    PGID=1000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fuellog ./fuellog
COPY migrations ./migrations
COPY alembic.ini ./
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Left empty for local/branch builds so the footer shows fuellog.__version__.
# CI passes the real version for tagged releases.
ARG APP_VERSION=
ENV APP_VERSION=$APP_VERSION

# A fixed app user/group. The entrypoint re-maps it to PUID/PGID at runtime
# and fixes ownership of the mounted /data before dropping privileges.
RUN groupadd -g 10001 appuser \
    && useradd -u 10001 -g appuser -d /app -s /usr/sbin/nologin appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Starts as root so the entrypoint can chown /data, then drops to the app user.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "fuellog.main:app", "--host", "0.0.0.0", "--port", "8000"]
