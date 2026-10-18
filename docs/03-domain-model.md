# Domain Model

## Core entities

```text
User
Role
Organization
JurisdictionPack
JurisdictionPackVersion
ContractType
IntakeSchema
LegalSource
LegalSourceVersion
SourceChunk
Clause
ClauseVersion
ValidationRule
RiskPlaybook
RiskPlaybookRule
Contract
ContractRequest
ContractVersion
ContractSection
Evidence
GenerationRun
ValidationFinding
RiskFinding
NegotiationItem
Approval
ExportFile
AuditEvent
EvaluationFixture
EvaluationRun
```

## Important relationships

```text
JurisdictionPack
  └── PackVersion
      ├── ContractTypes
      ├── IntakeSchemas
      ├── Clauses
      ├── ValidationRules
      ├── RiskPlaybook
      └── Source references

Contract
  ├── ContractRequest
  ├── ContractVersions
  ├── GenerationRuns
  ├── ValidationFindings
  ├── RiskFindings
  ├── NegotiationItems
  ├── Approvals
  ├── ExportFiles
  └── AuditEvents
```

## Immutability rules

- Never mutate a finalized contract version.
- Create a new version for edits.
- Never overwrite an active legal source; create a new source version.
- Never overwrite an approved clause; create a new clause version.
- Never delete audit events.
```