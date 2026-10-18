# API Contracts

## Authentication

```text
POST /auth/login
POST /auth/logout
GET  /auth/me
```

## Contracts

```text
POST   /contracts
GET    /contracts
GET    /contracts/:id
PATCH  /contracts/:id
POST   /contracts/:id/interpret
POST   /contracts/:id/confirm-request
POST   /contracts/:id/plan
POST   /contracts/:id/generate
POST   /contracts/:id/validate
POST   /contracts/:id/approve
POST   /contracts/:id/export
GET    /contracts/:id/versions
GET    /contracts/:id/audit
```

## Sections

```text
POST /contracts/:id/sections/:sectionId/regenerate
PATCH /contracts/:id/sections/:sectionId
GET  /contracts/:id/sections/:sectionId/evidence
GET  /contracts/:id/sections/:sectionId/risks
```

## Sources

```text
POST   /admin/sources
GET    /admin/sources
GET    /admin/sources/:id
POST   /admin/sources/:id/process
POST   /admin/sources/:id/approve
POST   /admin/sources/:id/activate
POST   /admin/sources/:id/archive
GET    /admin/sources/:id/chunks
POST   /admin/sources/test-retrieval
```

## Packs

```text
POST   /admin/packs
GET    /admin/packs
GET    /admin/packs/:id
POST   /admin/packs/:id/validate
POST   /admin/packs/:id/activate
POST   /admin/packs/:id/archive
GET    /admin/packs/:id/diff
```

## Negotiation

```text
POST /contracts/:id/negotiations
POST /contracts/:id/negotiations/:itemId/analyze
POST /contracts/:id/negotiations/:itemId/propose
POST /contracts/:id/negotiations/:itemId/decide
```

Every endpoint should have:
- request schema;
- response schema;
- authorization;
- error format;
- audit event where relevant;
- tests.