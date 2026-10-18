---
description: Implement one feature using the Hannibal workflow.
---

Read AGENTS.md and the relevant docs.

Before coding:
1. Restate the feature.
2. Identify affected modules.
3. Identify schemas and database changes.
4. Identify API changes.
5. Identify UI states.
6. Identify tests.
7. Identify non-goals.

Then implement the smallest complete vertical slice.

After coding:
1. Run formatter.
2. Run linter.
3. Run typecheck.
4. Run tests.
5. Run relevant browser tests.
6. Ask the architect, QA, security, and domain reviewer to inspect the change.
7. Fix blockers.
8. Update documentation.
9. Report files changed and verification results.