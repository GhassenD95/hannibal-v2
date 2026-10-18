# Implementation Status

Last updated: 2026-10-07

## Frontend (apps/web) — full workspace

Next.js 15 App Router SPA behind a typed fetch client (`lib/api.ts`; Bearer token in
`localStorage`, 401 → `/login`), consuming every backend module through the
`/api/*` → API rewrite in `next.config.js` (`HANNIBAL_API_URL`, default
`http://127.0.0.1:8000` — the demo environment runs the API on **8001** because
port 8000 is occupied by an unrelated service).

- **Pages**: `/login`; authenticated shell + dashboard (`/`, paged 25/page);
  `/contracts/new` wizard (guided form or describe → extract → review);
  `/contracts/[id]` workspace with tabs — sections (inline edit, regenerate,
  in-place per-section evidence), validation (run + findings, blocker gating),
  risks, negotiation (analyze/propose/decide), approvals (blocker-gated human
  approval), versions (metadata-only, raw response view), export (authenticated
  blob download, approval + blocker gates), audit; `/admin` (packs, sources incl.
  test-retrieval, clauses); `/evaluation` (run + metric groups + run history);
  `/stories` component state gallery.
- **Internationalization (EN/FR/AR + RTL)**: client-side dictionary context
  (`lib/i18n/`, no new deps). `I18nProvider` in the root layout + `useI18n`
  hook (`t` for singular/interpolated text, `tn` for singular/plural via
  `...One`/`...Other` keys). Language persisted in `localStorage`
  (`hannibal.lang`), detected from `navigator.language` (ar → Arabic, fr →
  French, else English) when nothing is stored, and selectable via a segmented
  EN/FR/AR switcher in the shell nav. Arabic sets `documentElement.dir="rtl"`
  and `lang="ar"` after hydration; the initial client render stays `en`
  (SSR-safe — fixes React hydration error #418 caused by reading `localStorage`
  during `useState` initialization). All pages, workspace panels, admin tabs,
  and evaluation console are translated; `StatusBadge`/table data values remain
  backend identifiers. Directional utilities converted to Tailwind logical
  properties (`ms-`/`me-`/`ps-`/`pe-`/`text-start`/`border-s-`) so RTL mirrors
  layouts instead of breaking them.
- **Favicon**: `app/icon.svg` (brand `#1d4ed8` rounded square with "H") so
  Next.js emits `<link rel="icon">` (no console 404).
- **CI web-build gate**: `.github/workflows/ci.yml` + `hannibal-ci.yml` gained a
  `web-build` job (Node 22, npm cache, `npm ci`, `format:check`, `typecheck`,
  `build`) so frontend regressions fail CI alongside the backend suite.
- **Design system**: tokens from `docs/10-design-system.md` via `tailwind.config.ts`
  + `globals.css`; shadcn-style primitives in `components/ui/`; semantic HTML,
  skip link, visible `focus-visible` outlines, ARIA tabs with arrow-key
  navigation, one primary action per screen, warnings stated in text (never color
  alone), no decorative animation.

## Running vertical slice

The application runs end-to-end against PostgreSQL 17 + pgvector:

1. **Information Collector**: natural-language extraction → validated `ContractRequest`
   (`POST /information-collector/extract`, field validation, progress tracking).
2. **Retrieval**: full-text search over indexed `sourcechunk` content, jurisdiction-filtered
   (`POST /rag/search`, `POST /rag/evidence/{section_title}`).
3. **Planner**: builds `ContractPlan` with section decisions and linked evidence IDs
   (`POST /planner/{contract_id}`, `GET /planner/{contract_id}`).
4. **Validation**: deterministic rules (currency consistency, date validity, required sections,
   approved clauses) persist `ValidationFinding` rows per run
   (`POST /validation/{contract_id}` + summary / risk-analysis / findings endpoints).
5. **Rendering**: export eligibility check against open blocker findings, HTML/DOCX/PDF export
   with persisted `ExportResult` (`/rendering/{contract_id}/...`).
6. **AI providers**: mock LLM/embedding/reranker endpoints (`/ai/...`).

## Verification results (exact commands)

| Check | Command | Result |
|---|---|---|
| Unit + integration + security tests | `.venv/bin/python -m pytest tests/ -q` | **83 passed, 0 failed** (includes 11-test security suite) |
| Lint gate | `.venv/bin/python -m pylint apps/ --errors-only` | **exit 0** |
| Import check | `python -c "from apps.api.app.main import app"` | loads OK |
| Seed (idempotent) | `.venv/bin/python scripts/seed-demo-data.py` | seeded, safe to re-run |
| Live API smoke | `uvicorn apps.api.app.main:app --port 8001` | all endpoints 200 |
| Web type check | `npm run typecheck` (apps/web) | **exit 0** |
| Web formatter | `npm run format:check` (apps/web) | **All matched files use Prettier code style!** |
| Web production build | `HANNIBAL_API_URL=http://127.0.0.1:8001 npm run build` (apps/web) | **compiled successfully**, 9 routes, 0 type errors |
| Browser tests (dev stack) | `HANNIBAL_API_URL=http://127.0.0.1:8001 npx playwright test` (apps/web) | **18 passed, 0 failed** (4 spec files × desktop 1280px + mobile 375px) |
| Docker image build | `docker compose build` | **exit 0** (api + web images) |
| Docker stack health | `docker compose up -d` | postgres/api/web all **healthy** (web proxies `/api/*` to `http://api:8000`) |
| Container smoke | `curl -X POST http://127.0.0.1:3000/api/auth/login ...` | seeded admin token returned (rewrite + networking verified) |
| Browser tests (docker stack) | `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test` (apps/web) | **18 passed, 0 failed** |
| Web type check | `npm run typecheck` (apps/web) | **exit 0** |
| Web formatter | `npm run format:check` (apps/web) | **All matched files use Prettier code style!** |
| Web production build | `npm run build` (apps/web) | **compiled successfully**, 0 type errors |
| Browser tests (final) | `npx playwright test` (apps/web, after i18n) | **18 passed, 0 failed** |
| Overflow regression sweep | viewport widths 320/375/640/768/1024/1280 across `/`, `/contracts/new`, `/admin`, `/evaluation`, `/contracts/20`, `/stories` | **0 problems** after `relative` on Table wrapper (`apps/web/components/ui/table.tsx:14`) and `w-full sm:w-auto sm:flex-1 sm:min-w-72` on admin Forms (lines 199, 421) |

Web browser tests cover: invalid/valid login + logout + protected-route redirect,
dashboard table and status-text badges, admin/evaluation navigation, guided wizard
→ workspace creation, arrow-key tab navigation, running validation, versions /
approvals / export panels, in-place section evidence, and the component stories
states. They use system Chrome (`channel: "chrome"`), so no browser download is
needed.

Note: `next dev` and `next build` must not run simultaneously — a production
build replaces `.next/` and breaks the dev server's static chunks (404s) until
the dev server is restarted.

## Internationalization verification (live, docker stack)

- Dashboard EN shows "23 contracts"; switching to FR in the shell nav renders
  "23 contrats", "Contrats", "Tableau de bord" (nav + footer translated).
- Switching to AR sets `documentElement.lang="ar"` + `dir="rtl"`; workspace
  tabs, admin h1 ("الحزم القانونية والمصادر والبنود"), and evaluation h1
  ("بوابات الجودة الحتمية") render Arabic; headline metrics interpolate
  correctly ("extraction: 4 مقياس").
- No raw translation-key leakage in page text after toggling languages.
- 0 console errors on hard navigation with a stored non-EN language (hydration
  fix verified via Playwright console-message capture).

## Known remaining gaps

- **Auth hardening**: the auth module is wired (`/auth` router) and exercised
  end-to-end by API + browser tests (login, JWT decode, 401 → `/login`), but there is no
  login rate limiting / account lockout and no refresh-token rotation (single 30-minute
  access token).
- **pgvector ANN search**: retrieval currently uses PostgreSQL full-text search; vector
  similarity ranking is layered on once chunk embeddings are indexed (see docs/05-rag-and-evidence.md).
- **AI providers**: only mock implementations active; real providers return HTTP 501.
- **CI**: two overlapping workflow files (`.github/workflows/ci.yml`,
  `.github/workflows/hannibal-ci.yml`) run on the same events; consolidate into one.
  Both already run the backend suite (`pytest`, `pylint --errors-only`) and both now
  run the `web-build` job (`format:check` + `typecheck` + `npm run build`).
- **Stale Docker volume**: `hannibalv2_postgres_data` holds PostgreSQL 16 data incompatible
  with the pg17 image; the compose stack uses a fresh `pgdata` volume instead. Remove the old
  volume manually once its data is confirmed disposable.
- **Web linting**: no ESLint config exists in the repo, so `apps/web` ships `typecheck`
  (`tsc --noEmit`) + `format:check` (Prettier) instead of `next lint` (deprecated in Next 15
  and interactive on first run). Component states are documented on `/stories` rather than
  Storybook to avoid adding a dependency.
- **Responsive overflow (fixed Oct 2026)**: Two root-cause bugs were identified and fixed:
  (1) the `Table` component's `overflow-x-auto` wrapper lacked `relative`, causing
  `sr-only` screen-reader elements to escape and inflate document `scrollWidth` to ~770px
  on mobile/tablet — fixed by adding `relative` to the wrapper div in
  `apps/web/components/ui/table.tsx:14`, verified via Playwright measurement (770→360);
  (2) admin `FormField` fields used `min-w-72 flex-1`, overflowing by ~9px at 320px — fixed
  by `w-full sm:w-auto sm:flex-1 sm:min-w-72` at lines 199 and 421 of
  `apps/web/app/(app)/admin/page.tsx`. All viewport widths across key routes now pass
  `scrollWidth <= innerWidth` assertions.

## Structure notes

- `apps/api/app/modules/core/models.py` is the single source of truth for DB tables (all
  `table=True`); module `schemas.py` files hold pure DTOs / request bodies.
- Database access is centralized in `apps/api/app/modules/core/db.py` (`DATABASE_URL` env,
  default `postgresql+psycopg2://hannibal:hannibal@localhost:5432/hannibal`).
- `tests/conftest.py` guarantees schema creation and a minimal `contract` id 1 for contract-scoped
  tests, and re-aligns Postgres id sequences after explicit-id inserts.