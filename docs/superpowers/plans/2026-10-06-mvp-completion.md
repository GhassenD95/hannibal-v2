# Hannibal V2 MVP Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship the docs/01 MVP scope as a working monolith: FastAPI backend + Next.js frontend + Morocco legal pack, with the full contract lifecycle (interpret → confirm → plan → generate → validate → risk → negotiate → version → approve → export) and an evaluation console.

**Architecture:** Modular monolith. `apps/api` (FastAPI + SQLModel + PostgreSQL/pgvector) is the single source of truth; `apps/web` (Next.js 15 App Router + Tailwind) consumes its JSON API via CORS. Versioned legal packs as JSON in `legal-packs/`, importable through the admin API. Deterministic code over LLM everywhere the rule is deterministic; mock LLM provider for drafting/qualitative review (real providers return 501).

**Tech Stack:** Python/FastAPI + SQLModel + psycopg2/pgvector, passlib+bcrpt+py-jose (auth), python-docx + reportlab (export), Next.js 15 / React 19 / Tailwind (UI), pytest + pylint + Playwright (verification).

**Spec:** docs/00,01,02,03,04,05,06,07,10,11,12 + AGENTS.md (all quotes/values copied below). Plan argues from those.

## Global Constraints

- Laws/clauses must come from **approved, effective, active** sources only (docs/05, 11).
- Every legal-sensitive section must carry `evidence_ids` or `clause_ids`; unsupported → `needs_review`/`unsupported`, never silently authored (AGENTS).
- Versioned + immutable: packs, sources, clauses, contract versions (docs/03). Never mutate a finalized version.
- Human approval required before final export (AGENTS). Export blocked by any open `blocker` finding.
- `source_metadata` (not `metadata`) column name; all `List`/`Dict` model fields need `sa_type=JSON`; naive datetimes (`NaiveDatetime`); no raw LLM output rendered (AGENTS).
- Typed schemas at every API boundary; audit events for plan/generate/validate/approve/export/negotiate/activate; no full contracts in normal logs.
- Frontend per docs/10 tokens + AGENTS: semantic HTML, keyboard nav, visible focus, every state designed, one primary action per screen, animations < 300ms.
- Demo legal text must be labeled "Demo sample — legal review required" and never auto-claimed compliant (AGENTS: no compliance claim without defined jurisdiction/sources/test evidence).

## Review Focus

- Blocked/unsupported sections must still render (with status), never crash the export path.
- A source that is not `approved` must never be retrievable (both admin approval and retrieval gate).
- Cross-org access to another org's contract must 403 (org scoping on every contract query).
- Placeholder text in a section (`[X]`, `{amount}`) must produce a finding, not reach export silently.
- Export must fail with 400 listing blockers even if a contract was previously exported once.

---

### Task A1: Auth + RBAC + organization scoping

**Files:**
- Modify: `apps/api/app/modules/core/models.py` (add `Role`, `UserRole`; add `organization_id` to `Users`, `Contract`, `ContractRequest`)
- Create: `apps/api/app/modules/auth/security.py`, `apps/api/app/modules/auth/schemas.py`, rewrite `apps/api/app/modules/auth/router/auth.py`, `apps/api/app/modules/auth/service.py`
- Create: `apps/api/app/modules/auth/deps.py` (`get_current_user`, `require_roles`, `get_current_org`)
- Create: `tests/test_auth.py`, `tests/test_org_scoping.py`
- Modify: `apps/api/app/modules/core/db.py` (load `.env` via python-dotenv; `SECRET_KEY`/`ALGORITHM` from env, defaults for dev)

**Interfaces:**
- Produces: `POST /auth/login {email,password}` → `{access_token, token_type}`; `GET /auth/me` → `{id,email,name,organization_id,roles[]}`; dependency `current_user: Users`; `require_roles("admin", ...)`.

- [x] **Step 1:** Write failing tests: login success/failure, `/auth/me` valid+invalid token, admin-only route 403 for non-admin.
- [x] **Step 2:** Run tests → fail (no auth router wired).
- [x] **Step 3:** Add `Role(name)` + `UserRole(user_id, role_id)` tables; `organization_id` FK on Users/Contract/ContractRequest; seed admin user in `scripts/seed-demo-data.py` + `tests/conftest.py` (admin@hannibal.local / admin123, role admin, org 1).
- [x] **Step 4:** Implement security.py (bcrypt via passlib, JWT create/decode), auth router/service, deps.py; wire router in `main.py`; CORS middleware allow `http://localhost:3000`.
- [x] **Step 5:** Org-scoping helper `contract_org_filter(session, org_id)` used by contracts list/get; test cross-org 403.
- [x] **Step 6:** Run tests → pass. Lint gate + commit.

### Task A2: Legal pack content + admin APIs

**Files:**
- Create: `legal-packs/ma-service-agreement.json`, `legal-packs/ma-nda.json` (pack meta, contract types, intake schema, clauses, validation rules, risk playbook, sources with sample chunk text labeled DEMO)
- Create: `apps/api/app/modules/admin/router/packs.py`, `.../sources.py`, `.../clauses.py`
- Create: `apps/api/app/modules/admin/service.py` (pack import/validate/activate/archive/diff; source create/process/approve/activate/archive/chunks/test-retrieval; clause CRUD)
- Create: `tests/test_admin.py`
- Modify: `apps/api/app/main.py` (mount `/admin` routers)

**Interfaces:**
- Produces: `POST /admin/packs/import {path}` loads JSON (guard path traversal → only `legal-packs/*`); `POST /admin/packs`; `GET /admin/packs`; `POST /admin/packs/{id}/validate|activate|archive`; `GET /admin/packs/{id}/diff`; `POST /admin/sources`; `POST /admin/sources/{id}/approve|activate|archive`; `GET /admin/sources/{id}/chunks`; `POST /admin/sources/test-retrieval {query}`.

- [x] **Step 1:** Write failing tests: import pack JSON creates pack+version+types+schema+clauses+validation rules+risk playbook; activate sets status active; source not approved is excluded from `/rag/search`.
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Write both JSON packs (structure per models; DEMO-labeled sample text; single approved source per pack flagged `status: approved` via import if pack flag `autoApproveDemoSources: true`, else draft).
- [x] **Step 4:** Implement admin service + routers behind `require_roles("admin")`; import references the `Clause`/`ValidationRule`/`RiskPlaybook` models.
- [x] **Step 5:** Implement `GET /admin/sources/{id}/chunks` and `test-retrieval` (calls rag search_sources).
- [x] **Step 6:** Run tests → pass. Seed uses import path. Lint + commit.

### Task A3: Contract lifecycle core (interpret → confirm → list/get/patch + sections)

**Files:**
- Create: `apps/api/app/modules/contracts/schemas.py` (request/response bodies)
- Rewrite: `apps/api/app/modules/contracts/service.py`, `.../router/contracts.py`
- Create: `tests/test_contracts_lifecycle.py`

**Interfaces:**
- Produces (all org-scoped to current_user, audit events on each):
  `POST /contracts` `{mode: "guided"|"ai", intake...}` → ContractRequest; `POST /contracts/{id}/interpret` (AI description → facts); `POST /contracts/{id}/confirm-request` → creates Contract skeleton w/ sections from active pack intake schema (status `requested`); `GET /contracts` (list w/ filters); `GET /contracts/{id}`; `PATCH /contracts/{id}` (metadata only → bumps draft version); `GET/POST /contracts/{id}/sections`; `PATCH /contracts/{id}/sections/{sid}`; `GET /contracts/{id}/sections/{sid}/evidence`; `GET /contracts/{id}/sections/{sid}/risks`.
- Keep `/contracts` listing Contracts (not ContractRequest).

- [x] **Step 1:** Tests: wizard guided → confirm-request creates sections from pack schema; AI interpret fills facts; cross-org 403 on GET/PATCH.
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Rewrite service/router with typed bodies (extend `ConfirmRequest`, `SectionEditRequest`), org scoping, audit events.
- [x] **Step 4:** Section evidence endpoint = `get_evidence_for_section`; section risks = risk findings for section.
- [x] **Step 5:** Tests → pass; lint; commit.

### Task A4: Generation engine (two-pass, structured, persisted)

**Files:**
- Create: `apps/api/app/modules/generation/service.py`, `.../router/generation.py`, `.../schemas.py`
- Modify: `apps/api/app/modules/core/models.py` (add `GenerationRun`: contract_id, section_id, prompt_version, model, pack_version_id, source_ids[] (JSON), clause_ids[] (JSON), validation_version, input_snapshot (JSON), output_snapshot (JSON), status, created_at)
- Modify: `apps/api/app/modules/contracts/router/contracts.py` (wire `/plan`, `/generate`, `/sections/{sid}/regenerate`)
- Modify: `apps/api/app/modules/ai_providers/impl.py` (make MockLLMProvider.generate_section deterministic + structured: content, evidence_ids, facts_used, assumptions, abstain_reason)
- Create: `tests/test_generation.py`

**Interfaces:**
- Produces: `POST /contracts/{id}/plan` (reuse planner router/service, return ContractPlan); `POST /contracts/{id}/generate` → generates each planned section, persists ContractSection(status supported|needs_review|unsupported, clause_ids, evidence_ids, facts_used) + GenerationRun, uses active pack clauses/evidence only; `POST /contracts/{id}/sections/{sid}/regenerate`.

- [x] **Step 1:** Tests: generate creates all sections w/ valid evidence ids (resolvable to approved sources or approved clause ids); unsupported section → `needs_review` + no fabricated evidence; GenerationRun persisted with pack_version+clause+source ids; regenerate replaces one section + creates new ContractVersion.
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Model + generation service: context packaging (facts/plan/clauses/evidence/output schema per docs/06), section assembly, status assignment, GenerationRun persist, section-level post-check (placeholders → needs_review).
- [x] **Step 4:** Wire router; evidence sanitization: only include evidence whose source `status=approved` (server-side re-check).
- [x] **Step 5:** Tests → pass; lint; commit.

A1–A4 verified 2026-10-07 by the full gate rather than re-run red phases: `tests/test_auth.py`, `tests/test_admin.py`, `tests/test_contracts_lifecycle.py`, `tests/test_generation.py` (plus cross-org 403 cases in the security suite — `tests/test_org_scoping.py` from the file list was folded into it) all pass within `pytest tests/ -q` → 83 passed; routers live and exercised end-to-end by the browser tests.

### Task A5: Validation + Risk engines (extended)

**Files:**
- Modify: `apps/api/app/modules/validation/service.py` (add rules: placeholder, pack.match, clausestatus, sourcestatus, approval.status, export.rule), `.../router/validation.py`
- Create: `apps/api/app/modules/risks/service.py`, `.../router/risks.py`, `.../schemas.py`
- Create: `tests/test_validation_extended.py`, `tests/test_risks.py`

**Interfaces:**
- Produces: `POST /contracts/{id}/validate` (runs engine, persists findings + ValidationRun, updates contract status, audit); `GET /contracts/{id}/validation/summary`; `POST /contracts/{id}/risk` (deterministic from findings + mock-LLM qualitative review per section, persists RiskFinding); `GET /contracts/{id}/risks`.

- [x] **Step 1:** Tests: placeholder text `[Amount]` → placeholder finding; contract whose type has no active pack → pack.match blocker; evidence referencing non-approved source → sourcestatus high; approve with open blockers → 400; risk run persists findings per section.
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Extend validation rules; add risks service (reuse mock `review_draft`, typed output, persist).
- [x] **Step 4:** Wire contracts router endpoints; audit events.
- [x] **Step 5:** Tests → pass; lint; commit. (58 passed, pylint exit 0)

### Task A6: Versioning + Approval + Negotiation + Export (real formats)

**Files:**
- Create: `apps/api/app/modules/negotiation/router/negotiation.py`, `.../service.py`
- Create: `apps/api/app/modules/approvals/router/approvals.py`, `.../service.py`
- Modify: `apps/api/app/modules/rendering/service.py` (real DOCX via python-docx, PDF via reportlab), `.../router/rendering.py` (download endpoint), `apps/api/app/modules/contracts/router/contracts.py` (`/approve`, `/export`, `/versions`, `/audit`)
- Modify: `apps/api/app/modules/contracts/service.py` (`create_contract_version` snapshot JSON)
- Create: `tests/test_versioning_negotiation_export.py`
- Modify: `requirements.txt` (python-docx, reportlab)

**Interfaces:**
- Produces: `POST /contracts/{id}/approve` (requires zero open blockers); `GET /contracts/{id}/versions` (immutable snapshots); `GET/POST /contracts/{id}/negotiations` (list/create item); `POST /contracts/{id}/negotiations/{itemId}/analyze`; `.../propose`; `.../decide {decision}`; `POST /contracts/{id}/export {format}` (blocked 400 if open blocker OR (format != preview and no approval)); `GET /contracts/{id}/export/{export_id}/content` (bytes download).

- [x] **Step 1:** Tests: approve blocked with blockers then ok; PATCH creates immutable version snapshot (old snapshot unchanged); negotiate analyze/propose/decide update status; export blocked without approval for final format, allowed as html preview; real DOCX/PDF bytes produced (magic bytes check).
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Implement negotiation service (mock analyze/propose), approvals service, version snapshot helper, rendering real formats.
- [x] **Step 4:** Wire routers; audit on version/approve/export/negotiate-decision.
- [x] **Step 5:** Tests → pass; lint; commit. (66 passed, pylint exit 0)

### Task A7: Evaluation engine

**Files:**
- Modify: `apps/api/app/modules/core/models.py` (add `EvaluationFixture`, `EvaluationRun`)
- Create: `apps/api/app/modules/evaluation/service.py`, `.../router/evaluation.py`, `.../schemas.py`
- Create: `tests/test_evaluation.py`

**Interfaces:**
- Produces: `GET /admin/evaluation/fixtures` (from tests/evaluation/fixtures.json + DB); `POST /admin/evaluation/run` (runs all fixtures → per-fixture + aggregate metrics per docs/12: extraction P/R, retrieval R@5, planning recall, generation schema validity + evidence coverage, validation P/R, forbiddenClaims hit rate); `GET /admin/evaluation/runs` (persisted EvaluationRun with metric JSON).

- [x] **Step 1:** Tests: run evaluator on fixtures.json → returns typed metric dict with the documented keys; forbidden claim appear in findings raises hit; persisted run.
- [x] **Step 2:** Run → fail.
- [x] **Step 3:** Models + engine (drive IC/rag/plan/generate/validate via existing services, compute metrics), router. Fixed latent bug: `find_active_pack_and_type` now selects the active pack by the contract type it supports instead of the first active pack (NDA fixture previously matched the service pack). Router uses `Depends(admin_required)` (dependency, not plain call).
- [x] **Step 4:** Tests → pass (6 new, 72 passed); `pylint --errors-only apps/api` exit 0. Notes: validation findings are dicts not objects in the engine; evaluation module test re-activates demo packs (test_admin's activation demotes the NDA pack to draft, causing order-dependent failure).

### Task A8: Security hardening

**Files:**
- Create: `tests/security/test_security_cases.py`
- Modify: any router not yet enforcing org/RBAC.

**Interfaces:** Evidence: each security test case in docs/11 runs against the live app.

- [x] **Step 1:** Tests: user cannot access another org's contract; inactive source not retrieved; wrong jurisdiction excluded; malicious instruction in source text not executed (defense = docs are data, never prompts — assert no prompt field from source enters generation input unmarked); unauthorized user cannot activate pack; export cannot bypass blocker validation; expired source excluded (effective_date future); no secrets in `/` or logs.
- [x] **Step 2:** Run → fix gaps → pass. Fixed `search_sources`: SQL now filters `(effective_date IS NULL OR effective_date <= NOW())` so approved-but-not-yet-effective sources are excluded (the "expired source" case was failing). 11 tests: 83 passed; `pylint --errors-only apps/api` exit 0.

### Task A9: Frontend (apps/web) — full workspace

**Interfaces (consumes all `/api` endpoints above):**
- Pages: `/login`; shell with nav; `/` dashboard (contracts, states); `/contracts/new` wizard (guided + AI tabs → interpret → confirm); `/contracts/[id]` workspace (sections list w/ evidence per section, clause tag, status, inline edit, regenerate; validation list; risks; negotiation; approvals; versions; export preview + download); `/admin` (sources, clauses, packs import + activate, test-retrieval); `/evaluation` (run + metrics).
- Implementation notes: design tokens in `globals.css` from docs/10; App Router + `next.config` API rewrite `/api/*` → `http://127.0.0.1:8000/*` (repo runs the API on 8000, not 8001); `lib/api.ts` typed client; loading/empty/error/success states everywhere; keyboard nav + focus-visible; one primary action per screen; motion < 300ms.
- [x] **Step 1:** Trimmed root `package.json` workspaces to `["apps/web"]`; `npm install`; `next build` passes hello page (toolchain validated: Next 15.0.0, React 19, Tailwind 3, TS 5.6; had to add `typescript`/`@types/*` devDeps because `next build` tried to auto-install them via yarn on an unreachable registry).
- [x] **Step 2:** Tokens + global styles + shell (Login page working against `/auth/login`). `tailwind.config.ts`/`globals.css` carry docs/10 tokens (ink/muted/surface/line/primary/success/warning/danger/evidence); skip link + `focus-visible` outline; `lib/api.ts` typed fetch client (Bearer token in `hannibal_token` localStorage, 401 → `/login`); `components/ui/*` shadcn-style primitives (button, input, textarea, select, label, card, badge+StatusBadge, alert, tabs w/ arrow-key roving tabindex, table, states, form-field); `components/shell/*` session provider + nav; `/login` verified against `POST /auth/login`.
- [x] **Step 3:** Dashboard (status text badges, client-side paging 25/page, loading/empty/error/success) + `/contracts/new` wizard (guided form vs. describe→extract→review; per-field collector validation; creates request → confirm → redirect to workspace) end-to-end.
- [x] **Step 4:** Contract workspace `/contracts/[id]`: header + Plan/Generate primary actions, tabs (sections, validation, risks, negotiation, approvals, versions, export, audit); sections with inline edit, regenerate, per-section evidence opened in place (source, jurisdiction, article, excerpt, relevance); validation run + findings table w/ blocker gating; risk run + list; negotiation create/analyze/propose/decide (`{decision:"accepted"|"rejected"|"escalated"}`); approvals (blocker-gated, returns `approval_id`, not `{status}`); versions (metadata-only — API exposes no snapshot content, surfaced honestly + raw response view); export (blocker gate; docx/pdf need approval; content fetched as authenticated blob and saved); audit list + raw JSON.
- [x] **Step 5:** `/admin` (packs import/validate/activate/archive, sources approve/archive + test-retrieval hits, clauses create/archive) and `/evaluation` (fixtures count, run → 6 metric groups + `forbidden_claims_hit_rate`, per-fixture rows, run history). `/stories` component gallery documents every shared component state.
- [x] **Step 6:** `HANNIBAL_API_URL=http://127.0.0.1:8001 npm run build` green (9 routes, 0 type errors); Playwright e2e (`apps/web/tests/e2e`, 4 spec files × desktop + 375px mobile = **18 passed**): login/logout/401 gating, dashboard, admin+evaluation nav, wizard → workspace → keyboard tab nav → run validation → versions/approvals/export panels, in-place section evidence, stories states. Toolchain additions: `@playwright/test` (uses system Chrome, no browser download) + `prettier` with `format`/`format:check` scripts (repo had no formatter); `npm run typecheck` = `tsc --noEmit`.
- [x] **Step 7 (added during execution, user directive):** Internationalization — `apps/web/lib/i18n/` dictionaries + `I18nProvider`/`useI18n` (`t`/`tn`, `{param}` interpolation, `...One`/`...Other` plural keys), EN/FR/AR switcher in the shell nav, `localStorage`-persisted with `navigator.language` detection, Arabic sets `dir="rtl"`; converted every page, all 8 workspace panels, the facts editor, admin tabs, and evaluation console; migrated directional utilities to Tailwind logical properties (`ms-`/`me-`/`ps-`/`pe-`/`text-start`). Bugs found and fixed: plural lookup used `.one`/`.other` instead of the actual `...One`/`...Other` dictionary keys; hydration mismatch (React #418) fixed by keeping SSR render at `en` and applying the stored/detected language in a mount effect (verified 0 console errors on hard navigation with AR stored). Also added `app/icon.svg` favicon and a `web-build` CI gate (`format:check` + `typecheck` + `build`) to both workflow files. Verified live on the docker stack via Playwright (EN/FR numbers + translated nav, AR RTL + Arabic headings, no key leakage, 0 console errors) and re-ran the full gate: **18/18 e2e**, **83 pytest**, `pylint --errors-only` exit 0, `format:check` clean, typecheck + build green.
- Deviations: repo port 8000 is occupied by an unrelated service, so the API runs on **8001** and `HANNIBAL_API_URL` must be set for dev/build/e2e (`next.config` rewrite honors it, defaulting to 8000); running `next build` while `next dev` is up clobbers `.next` and 404s dev chunks — stop dev before building. API mismatches coded around: no `/api` router prefixes (rewrite strips), extract returns `{}` unless jurisdiction/contract_type present (client always sends jurisdiction), confirm-request returns `{kind:"contract", status:"requested", section_count}`, negotiation decide takes `{decision}`, approve returns `approval_id`, versions expose no snapshot, export content requires Bearer blob download.

### Task A10: Deliverables + full verification

- [x] **Step 1:** Dockerfiles `apps/api/Dockerfile`, `apps/web/Dockerfile` (both built from repo root context to preserve the `apps.*` package layout, npm-workspaces lockfile, `legal-packs/`, and `tests/evaluation/fixtures.json` paths the API resolves via `parents[5]`); root `.dockerignore`; `docker-compose.yml` runs postgres/api/web with healthchecks — removed the broken `worker` service (`python -m app.worker` doesn't exist), unused `redis`/`minio` (no code references), and the required `.env` env_file that made `up` fail (now `required: false`). Web image gets `HANNIBAL_API_URL=http://api:8000` as build arg + runtime env. Verified: `docker compose build` exit 0, `up -d` all three **healthy**, seeded via `docker compose exec api python scripts/seed-demo-data.py`, login through `http://127.0.0.1:3000/api/auth/login` returns a token. Run instructions documented in `README.md`. Stale `hannibalv2_postgres_data` volume (PG16 data) left untouched — compose uses a fresh `pgdata` volume.
- [x] **Step 2:** Full gate: `pytest tests/ -q` → **83 passed** (includes the 11-test security suite), `pylint apps/ --errors-only` → exit 0, `npm run build` → compiled successfully (9 routes), `format:check` + `typecheck` → clean, browser tests **18/18 against the dev stack** and **18/18 against the Docker stack** (`PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000`).
- [x] **Step 3:** Updated `docs/16-implementation-status.md` (frontend + delivery sections, refreshed verification table, fixed stale "auth not wired" gap — auth is wired and exercised; remaining gap is hardening only); added root `CHANGELOG.md` and `README.md`; `docs/05/06/07` behaviors demonstrated through the e2e flow (jurisdiction-filtered retrieval evidence per section, validated generation with `supported`/`needs_review` counts, deterministic validation findings gating export).

---

## Self-review notes

- Coverage: docs/01 items all present (A1-A7, A9); docs/04 endpoints via A3/A4/A5/A6/A7; docs/02 modules map to routers (auth, contracts, admin/packs+sources+clauses, retrieval, generation, validation, risks, negotiation, rendering/approvals, evaluation, audit). Packs live under `/admin/packs`, retrieval under `/rag`, planner under `/contracts/{id}/plan` + `/planner`.
- Deps added with reasons: python-docx/reportlab (DOCX/PDF per scope), python-dotenv (env config). No other new deps — i18n is client dictionaries, zero dependencies.
- No real LLM key available → mock provider deterministic; real providers remain 501 (documented, correct abstention behavior).
- Post-plan additions (user directive) landed in A9 Step 7: EN/FR/AR i18n with RTL, favicon, CI `web-build` gate. Plan checkboxes A1–A10 all checked; gates re-run green after i18n (18 e2e, 83 pytest, pylint/format/typecheck/build clean).