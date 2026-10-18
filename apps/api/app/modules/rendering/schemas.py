from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class DocumentModel(SQLModel):
    """Validated contract document model ready for rendering."""
    contract_id: int
    version_number: int
    title: str
    sections: List["SectionRender"] = []
    clause_references: List[str] = []
    evidence_references: List[str] = []
    placeholders: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SectionRender(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(default=None, foreign_key="documentmodel.id")
    title: str
    content: str
    order_index: int
    clause_ids: List[str] = []
    evidence_ids: List[str] = []
    is_complete: bool = False


class ExportRequest(SQLModel):
    contract_id: int
    version_number: int
    format: str  # docx, pdf, html
    include_annotations: bool = False
    watermark: Optional[str] = None
