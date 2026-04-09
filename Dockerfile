FROM node:24-slim AS node-base

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PORT=8080 \
    APP_ENV=prod \
    APP_HOST=127.0.0.1 \
    APP_PORT=8001

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/bin/corepack /usr/local/bin/corepack
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/bin/node /usr/local/bin/nodejs && corepack enable

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/
RUN cd apps/api && uv sync --frozen --no-dev

COPY apps/web/package.json apps/web/yarn.lock ./apps/web/
RUN cd apps/web && yarn install --frozen-lockfile

COPY . .

RUN cd apps/web && yarn build

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/healthz')" || exit 1

RUN groupadd -r appuser && useradd -r -g appuser -s /bin/false -d /app appuser
RUN chown -R appuser:appuser /app
USER appuser

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
