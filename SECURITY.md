# Security

## Threat Model

Scaffold is a **web application template** — it provides authentication, authorization, and a data layer for building production applications. It is **not** an agentic containment runtime. If your application includes LLM tool-calling, evaluate [Iron Curtain](https://github.com/provos/ironcurtain) or [OpenShell](https://github.com/NVIDIA/OpenShell) for sandboxing.

## Environment Behavior (`APP_ENV`)

The `APP_ENV` setting controls several security-sensitive behaviors:

| Behavior                  | `local` / `test` | Everything else |
|---------------------------|:-----------------:|:---------------:|
| Debug mode (Tornado)      | On                | Off             |
| Dev password login        | Allowed           | Blocked         |
| Dev auth bypass           | Allowed           | Blocked         |
| Secure cookies            | Off               | On              |
| Scheduler token required  | No                | Yes             |
| Session secret check      | Skipped           | Enforced        |

**Any value other than `local` or `test` is treated as production.** This includes `preview`, `staging`, `replit`, `fly`, `render`, etc.

## Rate Limiting

The in-memory rate limiter is **ephemeral and per-process**. It resets on every restart and is not shared across instances. For production deployments behind multiple replicas, add a centralized rate limiter (e.g., Redis-based).

## Email Domain Allow-List

When `AUTH_ALLOWED_EMAIL_DOMAINS` is empty, **all email domains are accepted**. Always configure an explicit allow-list for production.

## Production Deployment Checklist

- [ ] Set `APP_ENV` to `prod` (or any value other than `local`/`test`)
- [ ] Generate and set a unique `SESSION_SECRET`
- [ ] Generate and set `SCHEDULER_SHARED_TOKEN`
- [ ] Configure `AUTH_ALLOWED_EMAIL_DOMAINS`
- [ ] Configure a persistent rate limiter if running multiple replicas
- [ ] Set `BOT_PROTECTION_ENABLED=true` and `BOT_SECRET_KEY` for public-facing deployments
- [ ] Review and restrict `DATABASE_URL` credentials

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly via GitHub Security Advisories on this repository.
