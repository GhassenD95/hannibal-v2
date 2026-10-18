from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import NaiveDatetime
from sqlmodel import SQLModel, Field, Relationship, JSON


class ModelBase(SQLModel):
    pass


# ============================================================
# Organization and User models
# ============================================================

class Users(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    organization: Optional["Organizations"] = Relationship(back_populates="users")
    user_roles: list["UserRole"] = Relationship(back_populates="user")


class Organizations(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    users: list["Users"] = Relationship(back_populates="organization")


class Role(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # admin, reviewer, drafter, viewer
    description: Optional[str] = None


class UserRole(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, foreign_key="users.id")
    role_id: int = Field(default=None, foreign_key="role.id")
    user: Optional["Users"] = Relationship(back_populates="user_roles")
    role: Optional["Role"] = Relationship()


# ============================================================
# Jurisdiction Pack models
# ============================================================

class JurisdictionPack(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    version: str = "1.0.0"
    status: str = "draft"  # draft, active, archived
    pack_metadata: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)


class PackVersion(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pack_id: int = Field(default=None, foreign_key="jurisdictionpack.id")
    version_number: str
    status: str = "draft"
    release_date: NaiveDatetime = Field(default_factory=datetime.utcnow)
    effective_date: Optional[NaiveDatetime] = None
    contract_types: list["ContractType"] = Relationship(back_populates="pack_version")
    intake_schemas: list["IntakeSchema"] = Relationship(back_populates="pack_version")
    clauses: list["Clause"] = Relationship(back_populates="pack_version")
    validation_rules: list["ValidationRule"] = Relationship(back_populates="pack_version")
    risk_playbook: Optional["RiskPlaybook"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "RiskPlaybook.pack_version_id"}
    )
    source_references: list["SourceReference"] = Relationship(back_populates="pack_version")


# ============================================================
# Contract Type models
# ============================================================

class ContractType(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    pack_version_id: Optional[int] = Field(default=None, foreign_key="packversion.id")
    pack_version: "PackVersion" = Relationship(back_populates="contract_types")
    intake_schema_id: Optional[int] = Field(default=None, foreign_key="intakeschema.id")
    intake_schema: "IntakeSchema" = Relationship(back_populates="contract_types")
    section_definitions: list["SectionDefinition"] = Relationship(
        back_populates="contract_type",
        sa_relationship_kwargs={"foreign_keys": "SectionDefinition.contract_type_id"},
    )


class SectionDefinition(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_type_id: int = Field(default=None, foreign_key="contracttype.id")
    name: str  # camel/snake key, e.g. "payment"
    title: str  # display title, e.g. "Payment and Pricing"
    description: Optional[str] = None
    is_required: bool = True
    order_index: int = 0
    evidence_tags: List[str] = Field(default=[], sa_type=JSON)
    default_clause_titles: List[str] = Field(default=[], sa_type=JSON)
    status: str = "active"  # active, deprecated
    contract_type: Optional["ContractType"] = Relationship(back_populates="section_definitions")


# ============================================================
# Intake Schema models
# ============================================================

class IntakeSchema(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    pack_version_id: Optional[int] = Field(default=None, foreign_key="packversion.id")
    pack_version: "PackVersion" = Relationship(back_populates="intake_schemas")
    fields: list["IntakeField"] = Relationship(back_populates="intake_schema")
    contract_types: list["ContractType"] = Relationship(back_populates="intake_schema")


class IntakeField(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    schema_id: int = Field(default=None, foreign_key="intakeschema.id")
    field_name: str
    field_label: str
    field_type: str  # text, date, money, currency, duration, select, multi-select, yes/no, rich text, upload
    is_required: bool = False
    options: List[str] = Field(default=[], sa_type=JSON)
    order_index: int
    intake_schema: Optional["IntakeSchema"] = Relationship(back_populates="fields")


# ============================================================
# Legal Source models
# ============================================================

class LegalSource(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    jurisdiction: str
    source_type: str  # law, regulation, case, treatise, academic
    language: str
    version: str
    effective_date: Optional[NaiveDatetime] = None
    status: str = "draft"  # draft, indexed, approved, archived
    description: Optional[str] = None
    chunk_count: int = 0
    source_metadata: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)


class LegalSourceVersion(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(default=None, foreign_key="legalsource.id")
    version: str
    text: str
    page_count: Optional[int] = None
    effective_date: Optional[NaiveDatetime] = None
    source_metadata: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)


class SourceChunk(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    version_id: int = Field(default=None, foreign_key="legalsourceversion.id")
    content: str
    chunk_index: int
    article: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class SourceReference(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pack_version_id: int = Field(default=None, foreign_key="packversion.id")
    source_id: int = Field(default=None, foreign_key="legalsource.id")
    relevance_score: float = 0.0
    pack_version: Optional["PackVersion"] = Relationship(back_populates="source_references")


# ============================================================
# Validation and risk playbook models
# ============================================================

class ValidationRule(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    rule_type: str  # input, structure, consistency, evidence, source_applicability, risk, export
    severity: str  # blocker, high, warning
    applies_to: List[str] = Field(default=[], sa_type=JSON)  # contract types
    config: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    is_active: bool = True
    pack_version_id: Optional[int] = Field(default=None, foreign_key="packversion.id")
    pack_version: Optional["PackVersion"] = Relationship(back_populates="validation_rules")


class RiskPlaybook(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pack_version_id: int = Field(default=None, foreign_key="packversion.id")
    name: str
    rules: List[str] = Field(default=[], sa_type=JSON)


# ============================================================
# Clause models
# ============================================================

class Clause(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    clause_type: str  # mandatory, optional, fallback
    jurisdiction: str
    contract_type: str
    version: str = "1.0.0"
    status: str = "draft"  # draft, approved, archived
    pack_version_id: Optional[int] = Field(default=None, foreign_key="packversion.id")
    pack_version: "PackVersion" = Relationship(back_populates="clauses")
    description: Optional[str] = None


class ClausePreference(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    clause_id: int = Field(default=None, foreign_key="clause.id")
    priority: int = 1
    selected_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Contract models
# ============================================================

class ContractRequest(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    contract_type: str
    jurisdiction: str
    language: str = "fr"
    status: str = "draft"
    facts: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    selected_clauses: List[int] = Field(default=[], sa_type=JSON)
    evidence_ids: List[str] = Field(default=[], sa_type=JSON)
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[NaiveDatetime] = Field(default=None)


class Contract(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    contract_type: str
    jurisdiction: str
    language: str
    status: str  # draft, validated, approved, exported
    request_id: Optional[int] = Field(default=None, foreign_key="contractrequest.id")
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    created_at: Optional[NaiveDatetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[NaiveDatetime] = Field(default=None)
    sections: list["ContractSection"] = Relationship(back_populates="contract")
    versions: list["ContractVersion"] = Relationship(back_populates="contract")
    validation_findings: list["ValidationFinding"] = Relationship(back_populates="contract")
    risk_findings: list["RiskFinding"] = Relationship(back_populates="contract")
    negotiation_items: list["NegotiationItem"] = Relationship(back_populates="contract")
    export_files: list["ExportFile"] = Relationship(back_populates="contract")
    audit_events: list["AuditEvent"] = Relationship(back_populates="contract")


class ContractSection(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    title: str
    content: str
    order_index: int
    clause_ids: List[int] = Field(default=[], sa_type=JSON)
    evidence_ids: List[str] = Field(default=[], sa_type=JSON)
    facts_used: List[str] = Field(default=[], sa_type=JSON)
    status: str = "pending"  # pending, supported, needs_review, unsupported
    generated_at: Optional[NaiveDatetime] = Field(default=None)
    contract: Optional["Contract"] = Relationship(back_populates="sections")


class ContractVersion(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    version_number: int
    title: str
    content: str
    is_active: bool = False
    validated: bool = False
    approved: bool = False
    export_format: Optional[str] = None  # docx, pdf, html
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    contract: Optional["Contract"] = Relationship(back_populates="versions")


class ValidationFinding(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    rule_id: str
    severity: str  # blocker, high, warning
    title: str
    explanation: str
    location: str
    evidence_id: Optional[str] = None
    recommendation: Optional[str] = None
    status: str = "open"  # open, resolved, ignored
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    contract: Optional["Contract"] = Relationship(back_populates="validation_findings")


class RiskFinding(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    title: str
    severity: str  # blocker, high, warning
    explanation: str
    location: str
    recommendation: str
    status: str = "open"  # open, resolved, ignored
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    contract: Optional["Contract"] = Relationship(back_populates="risk_findings")


class NegotiationItem(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    original_clause_id: Optional[int] = Field(default=None, foreign_key="clause.id")
    counterparty_clause: Optional[str] = None
    hannibal_analysis: Optional[str] = None
    proposed_text: Optional[str] = None
    status: str = "pending"  # pending, accepted, rejected, escalated
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    contract: Optional["Contract"] = Relationship(back_populates="negotiation_items")


class Approval(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    version_id: Optional[int] = Field(default=None, foreign_key="contractversion.id")
    approver_id: int
    approved_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    approval_type: str  # human, automated
    notes: Optional[str] = None


class ExportFile(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    version_id: Optional[int] = Field(default=None, foreign_key="contractversion.id")
    format: str  # docx, pdf, html
    storage_path: str
    generated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, completed, failed
    contract: Optional["Contract"] = Relationship(back_populates="export_files")


class AuditEvent(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    event_type: str  # generation, validation, export, negotiation, approval
    event_data: dict = Field(sa_type=JSON)
    user_id: int
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    contract: Optional["Contract"] = Relationship(back_populates="audit_events")


# ============================================================
# Planning and collection models
# ============================================================

class ContractPlan(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    title: str
    description: Optional[str] = None
    sections_required: List[str] = Field(default=[], sa_type=JSON)
    sections_complete: List[str] = Field(default=[], sa_type=JSON)
    selected_clauses: List[int] = Field(default=[], sa_type=JSON)
    evidence_ids: List[str] = Field(default=[], sa_type=JSON)
    unresolved_decisions: List[str] = Field(default=[], sa_type=JSON)
    status: str = "pending"  # pending, approved, generated
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    generated_at: Optional[NaiveDatetime] = None


class SectionDecision(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    section_id: str
    section_title: str
    decision: str  # "approved", "needs_decision", "unsupported"
    selected_clause_id: Optional[int] = None
    assigned_evidence: List[str] = Field(default=[], sa_type=JSON)
    rationale: Optional[str] = None
    decided_at: Optional[NaiveDatetime] = None


class ClauseSelection(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    section_id: str
    clause_id: int
    clause_title: str
    clause_type: str  # mandatory, optional, fallback
    selected_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    reason: str = "Selected from approved clause library"


class CollectionStep(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g., "basics", "parties", "scope"
    order_index: int
    is_complete: bool = False
    validation_issues: List[str] = Field(default=[], sa_type=JSON)
    saved_state: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)


class CollectionProgress(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_request_id: int = Field(default=None, foreign_key="contractrequest.id")
    step_name: str
    completed: bool = False
    field_count: int = 0
    required_count: int = 0
    last_updated: NaiveDatetime = Field(default_factory=datetime.utcnow)


class ValidationRun(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    run_by: int
    status: str = "pending"  # pending, completed, failed
    findings_count: int = 0
    blockers: int = 0
    high_risks: int = 0
    warnings: int = 0
    started_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[NaiveDatetime] = None


class GenerationRun(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    prompt_version: str
    model: str
    pack_version_id: Optional[int] = Field(default=None, foreign_key="packversion.id")
    source_ids: List[str] = Field(default=[], sa_type=JSON)
    clause_ids: List[int] = Field(default=[], sa_type=JSON)
    validation_version: str = "1.0.0"
    input_snapshot: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    output_snapshot: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    status: str = "pending"  # pending, supported, needs_review, unsupported, failed
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class ExportResult(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    export_id: str
    contract_id: int = Field(default=None, foreign_key="contract.id")
    version_number: int
    format: str
    storage_path: str
    generated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, completed, failed, blocked
    blockers: List[str] = Field(default=[], sa_type=JSON)
    warnings: List[str] = Field(default=[], sa_type=JSON)


class EvaluationFixture(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fixture_id: str
    name: str
    jurisdiction: str
    contract_type: str
    input: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    expected_sections: List[str] = Field(default=[], sa_type=JSON)
    required_clauses: List[str] = Field(default=[], sa_type=JSON)
    expected_evidence: List[str] = Field(default=[], sa_type=JSON)
    expected_risks: List[str] = Field(default=[], sa_type=JSON)
    forbidden_claims: List[str] = Field(default=[], sa_type=JSON)
    source: str = "file"  # file, db
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class EvaluationRun(ModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_by: int
    status: str = "completed"
    total_fixtures: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    per_fixture: List[Dict[str, Any]] = Field(default=[], sa_type=JSON)
    started_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    completed_at: NaiveDatetime = Field(default_factory=datetime.utcnow)