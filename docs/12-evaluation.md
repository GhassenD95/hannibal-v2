# Evaluation and Metrics

## Fixture structure

```json
{
  "id": "fixture_service_001",
  "name": "Service agreement with IP transfer",
  "jurisdiction": "MA",
  "contractType": "service_agreement",
  "input": {},
  "expectedSections": [],
  "requiredClauses": [],
  "expectedEvidence": [],
  "expectedRisks": [],
  "forbiddenClaims": []
}
```

## Metrics

### Extraction

```text
Field precision
Field recall
Normalization accuracy
Ambiguity detection accuracy
```

### Retrieval

```text
Recall@5
Precision@5
MRR
Citation locator accuracy
Wrong-jurisdiction leakage
Expired-source retrieval rate
```

### Planning

```text
Required-section recall
Required-clause recall
Irrelevant-clause rate
Unresolved-decision recall
```

### Generation

```text
Schema validity
Factual consistency
Evidence coverage
Citation validity
Unsupported assertion rate
Human acceptance rate
```

### Validation

```text
Precision
Recall
False-positive rate
False-negative rate
```

### System

```text
Median latency
P95 latency
Cost per generation
Export success rate
Failure recovery rate
```

## Formal definitions

\[
\text{Evidence coverage}
=
\frac{\text{supported legal-sensitive sections}}
{\text{total legal-sensitive sections}}
\]

\[
\text{Citation validity}
=
\frac{\text{valid applicable citations}}
{\text{all citations}}
\]

\[
\text{Unsupported assertion rate}
=
\frac{\text{unsupported legal-sensitive assertions}}
{\text{all legal-sensitive assertions}}
\]

\[
Precision =
\frac{TP}{TP + FP}
\]

\[
Recall =
\frac{TP}{TP + FN}
\]

Do not report one overall "AI accuracy" number. Break accuracy into measurable dimensions.