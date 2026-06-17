# AGENTS.md

This repo is the scaffold monorepo: a Python API (`apps/api`, Tornado + Strawberry GraphQL + SQLAlchemy + Alembic, managed with `uv`) and a Next.js Pages Router web app (`apps/web`, managed with `yarn`).

Standard commands live in the `Makefile` and `README.md` (`make setup`, `make dev`, `make test`, `make lint`, `make typecheck`, `make security`). Project conventions live in `CLAUDE.md` and `.cursor/rules/*`.

## Cursor Cloud specific instructions

The startup update script only refreshes dependencies (`uv sync` in `apps/api`, `yarn install` in `apps/web`). `uv` (with Python 3.13) and Docker are already installed in the VM image. The notes below cover non-obvious caveats for starting services.

- **Docker daemon is not auto-started.** Postgres runs in Docker and `make dev`/`make setup` call `docker compose up -d db`, so start the daemon first or those commands fail. Start it in the background (e.g. a tmux session or `sudo dockerd &`), then verify with `docker info`. If you hit a socket permission error, run `sudo chmod 666 /var/run/docker.sock`. The daemon is pre-configured for this VM (`/etc/docker/daemon.json` uses the `fuse-overlayfs` storage driver with the containerd snapshotter disabled, required for Docker 29 here); do not change that config.
- **LLM provider for dev/testing.** The default `LLM_PROVIDER=local_qwen` makes `make dev` try to start a local Qwen runtime and requires a one-time `make llm_local_setup` (~4.5 GB download + Torch). To exercise the app (including note summarization) without that download, export `LLM_PROVIDER=mock` before `make dev`; the mock provider returns deterministic summaries and is what the test suite uses.
- **Ports:** web `http://127.0.0.1:3000`, API `http://127.0.0.1:8001` (health at `/api/healthz`), Postgres `5432`, local LLM runtime `8002` (only when `local_qwen`).
- **Local sign-in:** the `/login` page has a Development Quick Login (enabled only when `APP_ENV` is `local`/`test`). Default credentials: username `admin`, password `local-dev-password`.
- **Database:** migrations are applied with `cd apps/api && uv run alembic upgrade head` (also run by `make setup`/`make dev`). A SQLite fallback exists, but local dev defaults to the Dockerized Postgres.
- **`make security`** runs `pip-audit` and `yarn audit`, which report pre-existing advisories against the repo's pinned dependency versions and exit non-zero; the secret scan and `ruff --select S` checks pass.
