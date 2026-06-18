# AGENTS

## Cursor Cloud specific instructions

This is a monorepo with a Python API (`apps/api`: Tornado + Strawberry GraphQL + SQLAlchemy async + Alembic)
and a Next.js Pages Router web app (`apps/web`). Standard commands live in the `Makefile`, `README.md`,
`GETTING_STARTED.md`, and `CLAUDE.md` — prefer those rather than re-deriving commands.

### Environment baseline (already provisioned in the VM snapshot)

- `uv` (in `~/.local/bin`, on PATH) manages the backend and auto-provisions Python 3.13; the system `python3`
  is 3.12, so always run backend tooling through `uv run ...` / the Make targets, never bare `python3`.
- Node 22 + Yarn 1 (via corepack) are used for `apps/web`. `.nvmrc` requests Node 24 but `verify_setup` and
  `package.json` engines also accept Node 22, which is what is installed.
- Docker is installed for local Postgres. The `ubuntu` user is in the `docker` group, so fresh shells can run
  `docker` without sudo. The update script does NOT start Docker; start it yourself when needed (see below).

### Starting services

- Start everything with `make dev` (API on `:8001`, web on `:3000`, health at `:8001/api/healthz`). Keep it
  running; stop leftovers with `make dev_stop`.
- `make dev` runs `docker compose up -d db`, so the Docker daemon must be running first. If `docker info` fails,
  start it with `sudo service docker start`. If a fresh shell hits a socket permission error, either start a new
  login shell (to pick up the `docker` group) or run `sudo chmod 666 /var/run/docker.sock`.
- `.env.local` (gitignored) sets `LLM_PROVIDER=mock` so `make dev` does NOT require the optional ~4.5 GB local
  Qwen model. The `mock` provider returns deterministic summaries and is enough to exercise the note
  summarization flow. To use the real default model, run `make llm_local_setup` once (downloads ~4.5 GB plus
  Torch/Transformers) and remove the `LLM_PROVIDER` override.

### Sign in / smoke test

- Dev quick login (local/test only) on `/login`: username `admin`, password `local-dev-password`.
- Core flow: sign in, create a note on the home page, then "Summarize Note". The same flow over the API is:
  `POST /api/auth/password-login` (saves the session cookie) then GraphQL `createNote` / `summarizeNote` at `/graphql`.

### Checks (definition of done)

- `make test`, `make lint`, `make typecheck` all pass in this environment.
- `make security` currently FAILS at `pip-audit` due to pre-existing upstream CVEs in pinned dependencies
  (network/PyPI access works); the secret-scan step itself passes. This is a dependency-version issue, not an
  environment problem.
