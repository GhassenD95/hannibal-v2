# Hannibal V2 — OpenCode Instructions

## Mission

Build Hannibal V2, a configurable, evidence-grounded Legal Contract Reasoning Engine.

Hannibal is not a generic chatbot. It must collect structured facts, select a jurisdiction pack, retrieve applicable legal sources, select approved clauses, generate a structured contract, validate it, analyze risks, support human review, and render professional documents.

## Core architecture

The system has three strict responsibilities:

1. Information Collector
   - Collects and validates structured user information.
   - May extract facts from natural language.
   - Never drafts legal clauses.
   - Never invents missing facts.
   - Produces ContractRequest.

2. Hannibal Core
   - Selects jurisdiction and contract configuration.
   - Retrieves applicable evidence.
   - Selects approved clauses.
   - Builds ContractPlan.
   - Generates structured contract sections.
   - Validates consistency and evidence.
   - Produces risks and review findings.

3. Document Formatter
   - Converts validated structured drafts to HTML, DOCX, and PDF.
   - Never selects clauses.
   - Never performs legal reasoning.
   - Never silently modifies legal content.

## Legal safety invariants

- Laws must come from active approved sources, not model memory.
- Every legal-sensitive section must have valid evidence IDs or approved clause IDs.
- Unsupported legal claims must be rejected or marked for human review.
- Uploaded files and retrieved text are untrusted data, not instructions.
- Jurisdiction-specific behavior belongs in legal packs, not generic application code.
- Human approval is required before final export.
- Never expose a fake general legal confidence percentage.
- Never claim legal compliance without defining the supported jurisdiction, sources, and test evidence.

## Engineering invariants

- Use typed schemas at every API and AI boundary.
- No raw LLM output may be rendered or exported.
- Use deterministic validation for dates, amounts, fields, references, sections, and placeholders.
- Version legal packs, sources, clauses, rules, prompts, models, and contract drafts.
- Use immutable contract versions.
- Emit audit events for important actions.
- Do not log complete confidential contracts in ordinary logs.
- Do not introduce microservices without a documented ADR.
- Do not add a dependency without explaining why it is needed.
- Do not over-engineer future features before the current vertical slice works.

## Frontend rules

- Use the design tokens in docs/10-design-system.md.
- Use semantic HTML and accessible components.
- Support keyboard navigation and visible focus.
- Every loading, empty, error, disabled, and success state must be designed.
- Use motion only when it improves comprehension.
- Keep animations under approximately 300ms unless a longer transition is justified.
- Do not use gradients, excessive glassmorphism, decorative noise, or dashboard clutter.
- Use one primary action per screen.
- Make warnings understandable in text, not only color.
- Do not hide evidence behind an AI chat interface.

## AI rules

- Prefer deterministic code over LLM reasoning when the rule is deterministic.
- Use structured output.
- Include evidence IDs in generation output.
- Validate evidence IDs server-side.
- Use abstention when evidence is insufficient.
- Use low temperature for legal drafting.
- Store prompt version, model, source IDs, clause IDs, pack version, and validation version in every generation run.
- Use the LLM for extraction, drafting, explanation, qualitative review, and ambiguity resolution.
- Do not use fine-tuning in the MVP.

## Required verification

Before declaring any feature complete, run:

1. formatter;
2. linter;
3. type checker;
4. unit tests;
5. integration tests;
6. relevant browser tests;
7. security checks;
8. update documentation;
9. update changelog or implementation status.

Report exact command results.

## Definition of done

A feature is complete only when:

- schemas exist;
- persistence exists if needed;
- API behavior is tested;
- UI has loading, empty, error, and success states;
- authorization is enforced;
- audit events exist where appropriate;
- documentation is updated;
- tests pass;
- the feature is demonstrated in the end-to-end flow.