# Validation Architecture

## Rule categories

```text
InputRule
StructureRule
ConsistencyRule
EvidenceRule
SourceApplicabilityRule
RiskRule
ExportRule
```

## Rule engine

Each rule has:

```json
{
  "id": "currency.consistent",
  "type": "consistency",
  "severity": "blocker",
  "appliesTo": ["service_agreement"],
  "config": {
    "paths": [
      "commercialTerms.amount.currency",
      "sections.payment.currency"
    ]
  }
}
```

## Deterministic rules

Use code for:
- date comparisons;
- amount consistency;
- currency consistency;
- required fields;
- section existence;
- placeholder detection;
- source status;
- pack match;
- clause status;
- approval status.

## LLM rules

Use the model for:
- ambiguity;
- semantic contradiction;
- vague scope;
- unclear responsibility;
- unusual risk;
- language quality.

The result must still be a typed finding.