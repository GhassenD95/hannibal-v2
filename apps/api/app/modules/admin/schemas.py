from datetime import date
from typing import Optional, Dict, List
from pydantic import BaseModel


class PackImportRequest(BaseModel):
    path: str


class PackStatusRequest(BaseModel):
    status: str  # draft, active, archived


class SourceCreate(BaseModel):
    title: str
    jurisdiction: str = "MA"
    source_type: str = "law"
    language: str = "fr"
    version: str = "1.0.0"
    effective_date: Optional[date] = None
    description: Optional[str] = None
    metadata: Dict[str, str] = {}


class SourceStatusRequest(BaseModel):
    status: str  # draft, indexed, approved, archived


class RetrievalQuery(BaseModel):
    query: str
    top_k: int = 5


class ClauseCreate(BaseModel):
    title: str
    content: str
    contract_type: str
    clause_type: str = "optional"
    jurisdiction: str = "MA"
    version: str = "1.0.0"
    status: str = "draft"
    description: Optional[str] = None


class ChunkOut(BaseModel):
    id: int
    content: str
    chunk_index: int
    article: Optional[str] = None