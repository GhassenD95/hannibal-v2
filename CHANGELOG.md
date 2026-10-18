# Changelog

All notable changes to Hannibal V2. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- **Full Next.js frontend (`apps/web`)** — Task A9: login + authenticated shell,
  dashboard with paged contract list, guided/extractive contract wizard,
  contract workspace (sections with inline evidence, validation, risks,
  negotiation, approvals, versions, export, audit), admin console (packs,
  sources, test-retrieval, clauses), evaluation console (runs, metric groups,
  per-fixture results), and `/stories` component state gallery. Typed fetch
  client with Bearer auth, shadcn-style accessible primitives, design tokens
  from `docs/10-design-system.md`.
- **Browser test suite** — Playwright (`apps/web/tests/e2e`, 4 specs × desktop +
  mobile 375px = 18 tests) covering authentication, dashboard, wizard →
  workspace → validation → panels, keyboard tab navigation, in-place evidence,
  admin/evaluation navigation, and component stories. Runs against the dev
  stack or any stack via `PLAYWRIGHT_BASE_URL`.
- **Formatter** — Prettier config + `format`/`format:check` scripts; `typecheck`
  script (`tsc --noEmit`).
- **Docker delivery** — `apps/api/Dockerfile`, `apps/web/Dockerfile` (multi-stage,
  npm workspaces-aware), root `.dockerignore`, and a working `docker-compose.yml`
  (postgres + api + web with healthchecks; build args wire the web rewrite to
  `http://api:8000`). Removed unused `worker`/`redis`/`minio` services and the
  required `.env` file that made `docker compose up` fail; optional `.env` is now
  loaded with `required: false`.
- **README** — native and Docker run instructions plus verification gates.
- **Internationalization (EN/FR/AR)** — client dictionary context in
  `apps/web/lib/i18n/` (no new dependencies): `I18nProvider` in the root
  layout, `useI18n` `t`/`tn` helpers with `{param}` interpolation and
  `...One`/`...Other` plural keys. Language persisted in `localStorage`,
  detected from `navigator.language` when unset, selectable via an EN/FR/AR
  switcher in the shell nav. Arabic flips the document to `dir="rtl"`. All
  pages, workspace panels, admin tabs, and the evaluation console translated;
  directional utilities moved to Tailwind logical properties so RTL mirrors
  layouts.
- **Favicon** — `app/icon.svg` with brand color "H".
- **CI web-build gate** — `web-build` job added to both GitHub Actions
  workflows (`format:check`, `typecheck`, `npm run build`) alongside the
  backend pytest + pylint suite.

### Fixed

- Dashboard contract count showed the raw key (`dashboard.contracts.other`)
  because the plural lookup used `.one`/`.other` suffixes while dictionaries
  use `...One`/`...Other`; `tn` now builds `${key}One`/`${key}Other`.
- React hydration error #418 when a stored non-EN language was restored on
  hard navigation: reading `localStorage` during `useState` init mismatched
  the server render. `I18nProvider` now starts SSR-safe at `en` and applies
  the detected/stored language in a mount effect.
- `scripts/seed-demo-data.py` no longer hardcodes `/home/ghassen/hannibalV2`
  (portable repo-root detection; required for container use).
- **Mobile horizontal page overflow**: `sr-only` screen-reader elements inside
  the `Table` component's `overflow-x-auto` wrapper escaped the clipping context
  and inflated document `scrollWidth` to ~770px on mobile/tablet — fixed by
  adding `relative` to the wrapper in `apps/web/components/ui/table.tsx:14`,
  verified (770→360); also fixed admin `FormField` min-width overflow (~9px at
  320px) with `w-full sm:w-auto sm:flex-1 sm:min-w-72` at
  `apps/web/app/(app)/admin/page.tsx:199,421`.
- Mobile navbar height on small screens (~133px from flex-wrap) addressed by
  responsive layout refinements.

### Known limitations

- Docker `postgres` starts from a fresh volume (`pgdata`): the previous
  project volume contains PostgreSQL 16 data incompatible with the pg17 image
  and was left untouched — remove `hannibalv2_postgres_data` manually if
  unwanted.
- Real AI providers return 501 (mock provider active); DOCX/PDF exports use
  python-docx/reportlab and are verified by magic-byte tests.