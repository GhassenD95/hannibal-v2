from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ValidationRule(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    rule_type: str  # input, structure, consistency, evidence, source_applicability, risk, export
    severity: str  # blocker, high, warning
    applies_to: List[str] = []  # contract types
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ValidationFinding(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    rule_id: str
    severity: str  # blocker, high, warning
    title: str
    explanation: str
    location: str
    evidence_id: Optional[str] = None
    recommendation: Optional[str] = None
    status: str = "open"  # open, resolved, ignored
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RiskFinding(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    section_id: Optional[int] = Field(default=None, foreign_key="contractsection.id")
    title: str
    severity: str  # blocker, high, warning
    explanation: str
    location: str
    recommendation: str
    status: str = "open"  # open, resolved, ignored
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationRun(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(default=None, foreign_key="contract.id")
    run_by: int
    status: str = "pending"  # pending, completed, failed
    findings_count: int = 0
    blockers: int = 0
    high_risks: int = 0
    warnings: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None