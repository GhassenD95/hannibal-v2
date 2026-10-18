# RAG and Evidence Design

## Retrieval flow

```text
User request
  ↓
Legal question per section
  ↓
Pack filters
  ↓
Keyword retrieval
  ↓
Vector retrieval
  ↓
Authority/date reranking
  ↓
Evidence selection
  ↓
Generation context
```

## Evidence object

```json
{
  "id": "ev_001",
  "sourceId": "src_001",
  "sourceVersion": "2025.1",
  "title": "Official source",
  "jurisdiction": "MA",
  "language": "fr",
  "article": "12",
  "pageStart": 8,
  "pageEnd": 9,
  "excerpt": "...",
  "relevanceReason": "Supports payment obligations",
  "authority": "official",
  "status": "valid"
}
```

## Retrieval failure

If no adequate evidence exists:

```text
Hannibal could not find sufficient approved evidence for this issue.

The section may still be drafted from an approved internal clause, or it can be sent for human review.
```

Do not force the model to answer.

## Evidence coverage

Every section has one status:
- Supported by official source
- Supported by approved clause
- Supported by internal policy
- Based on user-provided facts
- Needs human review
- Unsupported
```