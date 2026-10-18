# UI Responsiveness Fix + Full-Flow E2E Coverage Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix mobile horizontal page overflow and centering issues, then expand the Playwright suite to test every user flow and feature in order, on desktop and mobile.

**Architecture:** Two real layout defects cause the symptoms. (1) The shared `Table` component renders `.sr-only` (screen-reader) elements that are `position: absolute` inside an `overflow-x-auto` wrapper with no positioned ancestor; their containing block becomes the viewport, so they push the document `scrollWidth` to ~770px on a 375px viewport on every page that renders a data table (dashboard, admin Sources/Clauses, evaluation, workspace panels). Verified: adding `relative` to the wrapper drops `scrollWidth` from 770→360. (2) Two admin search/import `FormField`s use `min-w-72 flex-1`, causing a 9px overflow at 320px viewports. Content itself is correctly centered at all widths ≥640 (`mx-auto w-full max-w-7xl`), confirmed by symmetric-margin measurement, so no centering change is needed beyond fixing the overflow leaks.

**Tech Stack:** Next.js 15 / React 19, Tailwind 3.4 (logical properties), Playwright (`apps/web/tests/e2e`, projects desktop 1280 + mobile 375), FastAPI backend at 8001 for e2e.

**Spec:** AGENTS.md (frontend + AI rules; Definition of Done), `docs/16-implementation-status.md` (verification matrix), existing e2e specs in `apps/web/tests/e2e/`.

## Global Constraints

- No new dependencies.
- Preserve all accessibility roles/names the current specs assert (tables, tabs, headings); `relative` on the scroll wrapper must not change `overflow-x-auto` clipping behavior for real table content.
- Keep existing tab names, button labels, and translation keys untouched.
- Do not log complete confidential contracts (AGENTS.md).
- Each e2e spec keeps the abort/abstain-friendly patterns: use unique `Date.now()` contract names, `fullyParallel: false`, `workers: 1`.
- No raw LLM output rendered; UI assertions use deterministic generated content produced by the mock providers, not model text.
- e2e requires native API on 8001 (see AGENTS-verified run script) and clearing `.next` + `tsconfig.tsbuildinfo` before the run.

## Review Focus

- **sr-only escape:** `.sr-only` is `position: absolute`; any component with `.sr-only` descendants inside a scroll container but without a positioned ancestor will stretch the page. Every new responsive assertion must check `document.documentElement.scrollWidth <= viewport width` with a tolerance for the scrollbar gutter (measured ≤ `viewport + 0` after fix; desktop shows `-15`).
- **Empty/loading states:** views that render tables only after data loads (evaluation history, admin Clauses) must not be asserted as "no overflow" unless the table is actually present; assert on visible content, then measure.
- **RTL:** after switching language to Arabic, the page sets `dir="rtl"`; the overflow assertion must pass in RTL too (absolute `left`/`right` leak direction is mirrored).
- **i18n persistence:** language is stored in `localStorage` key `hannibal.lang`; tests that switch language must restore `en` (or reload from a clean context) so later tests are deterministic.
- **One primary action per screen:** export is blocked until human approval — the export flow test must assert the blocked state (as the design intends) rather than demanding an unblocked export.

---

### Task 1: Root-cause fix — give the `Table` scroll wrapper a positioned ancestor

**Files:**
- Modify: `apps/web/components/ui/table.tsx`

**Interfaces:**
- Consumes: existing `cn(...)` helper and `Table` props (`caption`, `children`, `className`).
- Produces: a `<Table>` whose outer wrapper is `relative overflow-x-auto …`. No prop changes; all callers (dashboard, admin, evaluation, workspace panels, stories) unaffected.

- [ ] **Step 1: Confirm current defect with a failing measurement**

Run: the Playwright MCP / a scratch eval on `http://127.0.0.1:3000/` at viewport 375px, authenticated.
Expected (before fix): `document.documentElement.scrollWidth === 770`, viewport 375 → page overflows horizontally.

- [ ] **Step 2: Add `relative` to the wrapper in `apps/web/components/ui/table.tsx`**

In the wrapper div (`cn(..., className)` combining `w-full overflow-x-auto rounded-md border border-line bg-white`), add `relative` to the class string so `.sr-only` descendants have a positioned ancestor and are clipped by `overflow-x-auto`.

- [ ] **Step 3: Verify dashboard no longer overflows**

Run: same measurement as Step 1.
Expected: `scrollWidth === 360` (viewport 375), i.e. no horizontal page scroll. Confirm the visible table still scrolls internally (`.overflow-x-auto` intact).

- [ ] **Step 4: Sweep all routes × widths for overflow regression**

Flow (authenticated, viewport sweep): `/`, `/contracts/new`, `/admin` (Sources + Clauses tabs), `/evaluation`, `/contracts/20` (all 8 workspace tabs), `/stories` at widths `[320, 375, 414, 640, 768, 1024, 1280, 1440]`.
Expected: `scrollWidth <= viewport` everywhere; symmetric centered content margins at ≥640.

- [ ] **Step 5: Run the existing e2e suite**

Run: clear `.next` and `tsconfig.tsbuildinfo`, then `npx playwright test` in `apps/web` with the native API running.
Expected: 18 passed (desktop + mobile projects).

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/ui/table.tsx
git commit -m "fix(web): anchor sr-only table elements to clip horizontal overflow"
```

---

### Task 2: Fix admin import/search field minimum-width overflow at 320px

**Files:**
- Modify: `apps/web/app/(app)/admin/page.tsx:199` and `:421`

**Interfaces:**
- Consumes: existing `FormField` component with `className="min-w-72 flex-1"`.
- Produces: form fields that lay out full-width on mobile and keep the min-width only from `sm` up. No prop change.

- [ ] **Step 1: Reproduce the 320px overflow**

Run: Playwright on `/admin` at viewport 320px.
Expected (before fix): `scrollWidth === 329`; overflowing elements are `DIV.flex.flex-col.gap-1.5.min-w-72` (the import-path field at line 199, and/or the retrieval-query field at line 421 when the Sources tab is active).

- [ ] **Step 2: Make the two `FormField` widths responsive**

Change `className="min-w-72 flex-1"` to `className="w-full sm:min-w-72 sm:flex-1"` at both lines (199 and 421). On `flex flex-wrap items-end gap-3` forms the field now takes the full row on mobile.

- [ ] **Step 3: Verify 320px admin is clean**

Run: `/admin` at 320px, and `/admin` Sources tab at 320px (the retrieval form).
Expected: `scrollWidth <= 320` in both.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/\(app\)/admin/page.tsx
git commit -m "fix(web): make admin import/search fields responsive at 320px"
```

---

### Task 3: Add a reusable no-horizontal-overflow assertion + centering check

**Files:**
- Modify: `apps/web/tests/e2e/helpers.ts`
- Test: coverage lands via the specs updated in Task 4 (all existing + new specs call this helper).

**Interfaces:**
- Consumes: nothing; pure page-state assertion helpers.
- Produces:
  - `expectNoHorizontalOverflow(page: Page): Promise<void>` — asserts `scrollWidth <= innerWidth` (tolerance 0; allows `-15` scrollbar gutter).
  - `expectCentered(page: Page): Promise<void>` — given the `#main` content container, asserts left/right margins within 2px of each other at widths ≥ 640.

- [ ] **Step 1: Write the helpers**

Append to `apps/web/tests/e2e/helpers.ts`:

```ts
export async function expectNoHorizontalOverflow(page: Page) {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

export async function expectCentered(page: Page) {
  const margins = await page.evaluate(() => {
    const content = document.querySelector('main#main > div');
    if (!content) return null;
    const r = content.getBoundingClientRect();
    return { left: r.left, right: window.innerWidth - r.right };
  });
  expect(margins).not.toBeNull();
  expect(Math.abs(margins!.left - margins!.right)).toBeLessThanOrEqual(2);
}
```

- [ ] **Step 2: Verify helpers on `/` desktop and mobile**

Run: two quick Playwright checks (desktop 1280, mobile 375) after Task 1 + 2 are in place.
Expected: `expectNoHorizontalOverflow` passes both; `expectCentered` passes at 1280.

- [ ] **Step 3: Commit**

```bash
git add apps/web/tests/e2e/helpers.ts
git commit -m "test(web): add no-overflow and centering e2e helpers"
```

---

### Task 4: Wire responsive assertions into every existing spec

**Files:**
- Modify: `apps/web/tests/e2e/auth.spec.ts`, `dashboard.spec.ts`, `workspace.spec.ts`, `stories.spec.ts`

**Interfaces:**
- Consumes: `expectNoHorizontalOverflow`, `expectCentered` from Task 3.
- Produces: desktop+mobile projects both asserting no page-level horizontal scroll on every route they visit.

- [ ] **Step 1: Assert no overflow at the end of each existing test**

In each of the 4 specs, call `await expectNoHorizontalOverflow(page)` at the end of every `test(...)`; call `await expectCentered(page)` in the dashboard and auth success tests (desktop-metric). Verify each still passes when run in the workspace and stories specs which visit `/` first (mobile project included).

- [ ] **Step 2: Run the expanded suite**

Run: clear `.next` + `tsconfig.tsbuildinfo`, `npx playwright test`.
Expected: all previous assertions still pass; new overflow/centering assertions green for both projects.

- [ ] **Step 3: Commit**

```bash
git add apps/web/tests/e2e/*.spec.ts
git commit -m "test(web): assert no horizontal overflow and centering across e2e specs"
```

---

### Task 5: Full workspace flow — every tab end-to-end on a generated contract

**Files:**
- Create: `apps/web/tests/e2e/full-flow.spec.ts`

**Interfaces:**
- Consumes: `login`, `selectTab`, `openContract`, `expectNoHorizontalOverflow` from helpers.
- Produces: one ordered test proving the complete workspace vertical slice on a real generated contract.

- [ ] **Step 1: Write the full-flow test**

One `test` that, in order:
1. `login(page)`; open `/contracts/new`; Continue; fill unique name; `service_agreement`; `MA`; Create contract → workspace.
2. Sections tab → `Generate draft` → wait for plan acceptance (`Generate draft` disabled or status text appears); open the evidence button; assert "Evidence for" panel.
3. Validation tab → `Run validation` → assert blocker/empty state text.
4. Risks tab → `Run risk analysis` → assert results appear.
5. Negotiation tab → add an item via the form → assert it lists.
6. Versions tab → create a version → assert version row + "version numbers, flags, and timestamps" text.
7. Approvals tab → submit reviewer approval (login as reviewer if the UI enables it) — at minimum assert the human-approval panel and an approval action exists.
8. Export tab → assert export is blocked (design intent) with a clear warning.
9. Audit tab → assert an audit trail entry exists for the generate action.
10. `await expectNoHorizontalOverflow(page)`.

Mark known mock-provider caveats as comments only if the step must be tolerant.

- [ ] **Step 2: Run and iterate**

Run: `npx playwright test full-flow.spec.ts`.
Expected: PASS across both projects. If a backend mock returns an abstention/empty result, assert the designed empty state instead of a value.

- [ ] **Step 3: Commit**

```bash
git add apps/web/tests/e2e/full-flow.spec.ts
git commit -m "test(web): cover complete workspace flow end-to-end"
```

---

### Task 6: i18n language switching + RTL responsive coverage

**Files:**
- Create: `apps/web/tests/e2e/i18n.spec.ts`

**Interfaces:**
- Consumes: `login`, `expectNoHorizontalOverflow`, `expectCentered` from helpers.
- Produces: proof that EN/FR/AR all render with no key leakage, AR applies `dir="rtl"`, and overflow/centering hold in RTL.

- [ ] **Step 1: Write the i18n flow test**

One `test`:
1. `login(page)`; reset `localStorage.hannibal.lang = 'en'` via `page.addInitScript` (or a goto to `/` + reload).
2. Assert an EN-specific heading string, e.g. Dashboard/H1 `Dashboard`.
3. Switch to French via the language switcher → assert a FR-only localized string is present and no `t(` key leakage in `document.body.innerText`.
4. Switch to Arabic → assert `document.documentElement.dir === 'rtl'` and an AR-only localized string present; run `expectNoHorizontalOverflow(page)` and `expectCentered(page)`.
5. Switch back to English (cleanup) so later tests are unaffected.

Assert actual translation strings from `apps/web/lib/i18n/dictionaries.ts` (hardcode the EN/FR/AR values for the chosen keys).

- [ ] **Step 2: Run and iterate**

Run: `npx playwright test i18n.spec.ts`.
Expected: PASS both projects. Fix any FR/AR dictionary gaps surfaced (like the earlier `{count}` fix) rather than weakening assertions.

- [ ] **Step 3: Commit**

```bash
git add apps/web/tests/e2e/i18n.spec.ts
git commit -m "test(web): cover EN/FR/AR switching and RTL responsiveness"
```

---

### Task 7: Admin + evaluation flows — feature-level coverage

**Files:**
- Create: `apps/web/tests/e2e/admin-evaluation.spec.ts`

**Interfaces:**
- Consumes: `login`, `selectTab`, `expectNoHorizontalOverflow` from helpers.
- Produces: admin tabs (Legal packs, Sources, Clauses) and evaluation page verified with deterministic content.

- [ ] **Step 1: Write the admin flow test**

1. `login(page)`; goto `/admin`.
2. Assert Legal packs tab lists packs (deterministic cards) — one primary action per screen.
3. Sources tab → run the retrieval test with a deterministic query → assert evidence rows + source metadata render.
4. Clauses tab → assert approved clauses list renders.
5. `expectNoHorizontalOverflow(page)` at end.

Caveat: retrieval is FTS + mock embeddings against the seeded sources; assert on seeded source names/IDs rather than freeform results.

- [ ] **Step 2: Write the evaluation flow test**

1. `login(page)`; goto `/evaluation`.
2. Assert metric fixtures render (abstention must be represented, not a fake confidence).
3. `Run evaluation` → wait for results → assert a recorded run appears in the history table.
4. `expectNoHorizontalOverflow(page)`.

- [ ] **Step 3: Run and iterate**

Run: `npx playwright test admin-evaluation.spec.ts`.
Expected: PASS both projects.

- [ ] **Step 4: Commit**

```bash
git add apps/web/tests/e2e/admin-evaluation.spec.ts
git commit -m "test(web): cover admin and evaluation flows"
```

---

### Task 8: Gate re-run + documentation

**Files:**
- Modify: `docs/16-implementation-status.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: results of Tasks 1-7.
- Produces: updated verification matrix and changelog entries.

- [ ] **Step 1: Run all web gates**

Run (in `apps/web`): clear `.next` + `tsconfig.tsbuildinfo`; `npm run format:check`; `npm run typecheck`; `npm run build`; `npx playwright test` (full suite).
Expected: all exit 0; e2e count reflects the new specs across both projects.

- [ ] **Step 2: Run backend gates**

Run (repo root): `PYTHONPATH=. .venv/bin/pylint --errors-only apps/`; `pytest tests/ -q`.
Expected: pylint exit 0; pytest green (existing count).

- [ ] **Step 3: Rebuild docker web and smoke-test**

Run: `docker compose build web && docker compose up -d web`, then `curl http://127.0.0.1:3000/`.
Expected: 200; no console errors on `/contracts/20`.

- [ ] **Step 4: Update docs**

In `docs/16-implementation-status.md`: add the responsive fix + new e2e counts to the verification table. In `CHANGELOG.md`: add "Fixed: mobile horizontal page overflow from sr-only table elements; 320px admin form overflow" and "Added: full-flow, admin, evaluation, i18n e2e coverage".

- [ ] **Step 5: Commit**

```bash
git add docs/16-implementation-status.md CHANGELOG.md
git commit -m "docs: record responsive fixes and expanded e2e coverage"
```