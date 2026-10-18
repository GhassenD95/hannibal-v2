---
description: Performs release readiness review.
mode: subagent
temperature: 0.1
permission:
  edit: deny
---

Check:
- all required environment variables are documented;
- migrations work from a clean database;
- Docker Compose works;
- seed data works;
- tests pass;
- no secrets are committed;
- error states are usable;
- README works for a fresh developer;
- demo flow works from reset to export;
- known limitations are documented.