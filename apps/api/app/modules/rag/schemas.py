from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class LegalSource(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    jurisdiction: str
    source_type: str  # law, regulation, case, treatise, academic
    language: str
    version: str
    effective_date: Optional[datetime] = None
    status: str = "draft"  # draft, indexed, approved, archived
    description: Optional[str] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LegalSourceVersion(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(default=None, foreign_key="legalsource.id")
    version: str
    text: str
    page_count: Optional[int] = None
    effective_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceChunk(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    version_id: int = Field(default=None, foreign_key="legalsourceversion.id")
    content: str
    chunk_index: int
    article: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class SourceReference(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    pack_version_id: int = Field(default=None, foreign_key="packversion.id")
    source_id: int = Field(default=None, foreign_key="legalsource.id")
    relevance_score: float = 0.0
    jurisdiction_filter: str = ""
    contract_type_filter: str = ""
    language_filter: str = ""


class Evidence(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str
    source_version: str
    title: str
    jurisdiction: str
    language: str
    article: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    excerpt: str
    relevance_reason: str
    authority: str = "official"
    status: str = "valid"