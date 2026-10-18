# Implementation rule

Build Hannibal as a complete vertical slice, not as disconnected mock screens.

Every stage must produce a typed, inspectable artifact:

Information Collector:
ContractRequest

Jurisdiction Pack:
ActivePackVersion

Retrieval:
Evidence[]

Planner:
ContractPlan

Generation:
StructuredContractDraft

Validation:
ValidationReport

Risk:
RiskReport

Negotiation:
NegotiationAnalysis

Approval:
ApprovedContractVersion

Formatter:
HTML/DOCX/PDF

No stage may silently bypass the previous stage.

When uncertain, prefer:
- explicit configuration;
- typed schemas;
- deterministic validation;
- human review;
- abstention;
- traceability;
- simple architecture;
- tested behavior.

Do not optimize for the number of AI features.
Optimize for a trustworthy, configurable, reviewable legal contract pipeline.