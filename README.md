# Hannibal V2

Configurable, evidence-grounded legal contract reasoning engine. Hannibal
collects structured facts, selects a jurisdiction pack, retrieves approved legal
sources, generates a validated contract, analyzes risks, supports human review
and approval, and exports professional documents.

Architecture, domain, API contracts, and safety invariants live in [`docs/`](docs/):

- [00 Product vision](docs/00-product-vision.md) · [01 Scope](docs/01-scope.md)
- [02 Architecture](docs/02-architecture.md) · [03 Domain model](docs/03-domain-model.md)
- [04 API contracts](docs/04-api-contracts.md) · [10 Design system](docs/10-design-system.md)
- [11 Security](docs/11-security.md) · [16 Implementation status](docs/16-implementation-status.md)

## Repository layout

```
apps/api     FastAPI backend (modules: auth, information-collector, contracts,
             rag, planner, validation, risks, negotiation, rendering,
             evaluation, admin, ai_providers)
apps/web     Next.js 15 App Router frontend (TypeScript, Tailwind, shadcn-style UI)
legal-packs  Versioned jurisdiction packs (JSON) imported through the admin API
scripts      Database seed and setup helpers
tests        Backend test suite + evaluation fixtures
docs         Product, architecture, and implementation documentation
```

## Quick start (native development)

Requirements: Python 3.11+, Node 20+, PostgreSQL 17 with the `pgvector` extension.

```bash
# 1. Database (any PostgreSQL 17 + pgvector; adjust DATABASE_URL to match)
#    DATABASE_URL=postgresql+psycopg2://hannibal:hannibal@localhost:5432/hannibal

# 2. Backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg2://hannibal:hannibal@localhost:5432/hannibal \
  .venv/bin/uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8001

# 3. Seed demo data (idempotent; demo admin + jurisdiction packs + sample contract)
.venv/bin/python scripts/seed-demo-data.py

# 4. Frontend (separate terminal; HANNIBAL_API_URL is what /api/* proxies to)
npm install
cd apps/web && HANNIBAL_API_URL=http://127.0.0.1:8001 npm run dev -- --port 3100
```

Open <http://127.0.0.1:3100> and sign in with the seeded demo admin
(`admin@hannibal.local` / `admin123` — demo data only, rotate for any real
deployment).

> If another service already occupies port 8000, run the API on a free port and
> point `HANNIBAL_API_URL` at it. `apps/web/next.config.js` proxies
> `/api/* → ${HANNIBAL_API_URL}/` (default `http://127.0.0.1:8000`).

## Quick start (Docker)

```bash
docker compose up -d --build          # postgres + api (:8010 loopback) + web (:3000)
docker compose exec api python scripts/seed-demo-data.py
```

Open <http://127.0.0.1:3000>. Containers start healthy (`pg_isready`, API `/`,
web `/login` healthchecks); the web image proxies `/api/*` to `http://api:8000`
on the compose network. To reset the database, ask before removing volumes
(`docker compose down -v` deletes data).

## Verification gates

```bash
# Backend
.venv/bin/python -m pytest tests/ -q                 # unit + integration
.venv/bin/python -m pylint apps/ --errors-only       # lint gate

# Frontend (apps/web)
npm run format:check                                 # Prettier
npm run typecheck                                    # tsc --noEmit
HANNIBAL_API_URL=http://127.0.0.1:8001 npm run build # production build

# Browser tests (Chrome required; start the stack first)
cd apps/web
HANNIBAL_API_URL=http://127.0.0.1:8001 npx playwright test                 # dev stack
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test              # docker stack
```

Note: stop `next dev` before `next build` — a production build replaces
`.next/` and breaks a running dev server until it is restarted.

## Documentation and AI conventions

Legal content is never generated from model memory: every legal-sensitive
section must reference approved clause IDs or evidence IDs from active source
versions, unsupported claims are rejected or flagged for human review, and
final export always requires human approval. See `AGENTS.md` for the full
engineering and legal-safety invariants.
