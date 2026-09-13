# CLAUDE.md

Guidance for Claude Code (or any AI coding agent) working in this repository.

## Project Summary

FoodFlow is a full-stack, AI-powered food-delivery platform built as a portfolio project. It connects four user roles — customers, restaurant managers, delivery riders, and administrators — through one FastAPI application with server-rendered Jinja2 templates, Tailwind CSS, and vanilla JavaScript on the frontend.

The full functional and technical specification lives in [`task.md`](./task.md). Treat it as the source of truth for scope, data models, API routes, order-status rules, and AI agent responsibilities. Read it before making non-trivial changes.

## Architecture at a Glance

```text
app/
├── main.py          # FastAPI app factory, route registration, template/static wiring
├── config.py        # Environment-based settings (OpenAI key/model, secrets)
├── dependencies.py  # Auth + role-based access dependencies
├── models/          # Internal data-layer representations (one file per entity)
├── schemas/         # Request/response DTOs used by routes
├── routes/          # FastAPI routers, grouped by resource
├── services/        # Business logic (auth, orders, delivery, payment, coupons)
├── agents/          # AI agents (one responsibility each, OpenAI SDK + rule-based fallback)
├── data/            # JSON-file mock data store (repository-pattern access only)
└── utils/           # Shared validation, pricing, and order-status-rule helpers
templates/           # Jinja2 HTML pages (customer, restaurant, rider, admin)
static/              # CSS, vanilla JS modules, images
tests/               # Pytest suite (backend + AI fallback behavior)
```

## Key Conventions

- **Data layer is swappable.** All persistence goes through the JSON-file repository helpers in `app/utils`/`app/services`, never raw file I/O in routes. This keeps a future PostgreSQL migration a data-layer-only change (see `task.md` §4).
- **Never trust client-submitted prices.** Cart/order totals are always recalculated server-side (`app/utils/pricing.py`). Coupons are re-validated server-side before being applied.
- **Order status is a strict state machine.** Valid transitions are defined in `app/utils/status_rules.py` and enforced in `order_service.py`. Invalid transitions must return a clear 4xx error, never silently succeed.
- **AI agents must degrade gracefully.** Every agent in `app/agents/` calls the OpenAI SDK when `OPENAI_API_KEY` is configured, but must fall back to a deterministic, rule-based implementation using real mock data when no key is set or the API call fails. The app must be fully demoable with zero external API calls.
- **The support agent never fabricates outcomes.** It must not claim a refund, cancellation, or account change occurred unless the backend actually confirms it.
- **The risk/fraud agent only flags, never punishes.** Automated account or order actions based on fraud signals require human review.
- **Secrets stay server-side.** API keys and secrets are read from environment variables (`.env`, never committed) and must never be exposed to frontend code or LocalStorage.
- **Mock auth is intentionally simple.** This MVP uses opaque bearer tokens rather than real session/JWT infrastructure — see `task.md` §18. Don't over-engineer auth beyond what the spec calls for unless asked.

## Working in This Repo

- Keep new backend code inside the existing `app/` module boundaries (models vs. schemas vs. services vs. routes vs. agents) rather than mixing concerns into a single file.
- Match the existing route paths under `/api/...` exactly as enumerated in `task.md` §11 — frontend JS in `static/js/` depends on those exact paths and payload shapes.
- Frontend pages extend a shared Jinja2 base layout; avoid duplicating navbar/footer markup across templates.
- When adding a page or feature, include its loading, error, and empty states (`task.md` §17) and accessibility basics (`task.md` §19) — these are treated as required, not optional polish.
- Run `pytest tests/ -q` after backend changes. There is no frontend build step; templates and static assets are served directly by FastAPI/Jinja2.
- See [`AGENTS.md`](./AGENTS.md) for a description of each AI agent's responsibilities and boundaries.

## Non-Goals for the MVP

Real payments, real authentication, a production database, WebSocket live tracking, and map/geolocation integrations are explicitly out of scope for this version (`task.md` §14, §24). Don't introduce these dependencies unless the user asks for the "future enhancements" path.
