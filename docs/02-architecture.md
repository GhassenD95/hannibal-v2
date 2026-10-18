# Architecture

## Modular monolith

```text
Frontend (Next.js + TypeScript + Tailwind)
  ├── Dashboard
  ├── New contract wizard
  ├── AI description mode
  ├── Contract workspace
  ├── Review/approval workflow
  ├── Negotiation workspace
  └── Admin studio

Backend (FastAPI + Python)
  ├── Authentication and authorization
  ├── Information Collector
  ├── Jurisdiction Pack Manager
  ├── Legal Source Ingestion
  ├── Hybrid Retrieval
  ├── Clause Library
  ├── Contract Planner
  ├── Structured Generation
  ├── Validation Engine
  ├── Risk Engine
  ├── Negotiation Engine
  ├── Document Formatter
  ├── Approval Workflow
  ├── Evaluation Engine
  └── Audit/Observability

Data
  ├── PostgreSQL
  ├── pgvector
  ├── Full-text search
  ├── Object storage (MinIO)
  └── Evaluation fixtures
```

## Module boundaries

Each module is independently testable with its own schemas and tests:

```
apps/api/src/modules/
  auth/
  contracts/
  jurisdiction-packs/
  sources/
  retrieval/
  clauses/
  planning/
  generation/
  validation/
  risks/
  negotiation/
  rendering/
  approvals/
  audit/
  evaluation/
```