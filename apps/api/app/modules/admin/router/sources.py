from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, LegalSource
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.auth.deps import admin_required
from apps.api.app.modules.admin import service
from apps.api.app.modules.admin.schemas import (
    SourceCreate, SourceStatusRequest, RetrievalQuery, ChunkOut,
)

router = APIRouter(prefix="/admin/sources", tags=["admin-sources"])


@router.get("")
def list_sources(
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return [
        {"id": s.id, "title": s.title, "jurisdiction": s.jurisdiction,
         "status": s.status, "version": s.version, "chunk_count": s.chunk_count,
         "effective_date": str(s.effective_date) if s.effective_date else None}
        for s in service.list_sources(session)
    ]


@router.post("")
def create_source(
    payload: SourceCreate,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    source = service.create_source(session, payload.model_dump())
    record_audit(session, "source_create", user_id=0,
                 source_id=source.id, title=source.title)
    return {"id": source.id, "title": source.title, "status": source.status}


@router.post("/{source_id}/approve")
def approve_source(
    source_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        source = service.set_source_status(session, source_id, "approved")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(session, "source_approve", user_id=0, source_id=source.id)
    return {"id": source.id, "status": source.status}


@router.post("/{source_id}/activate")
def activate_source(
    source_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        source = service.set_source_status(session, source_id, "indexed")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(session, "source_activate", user_id=0, source_id=source.id)
    return {"id": source.id, "status": source.status}


@router.post("/{source_id}/archive")
def archive_source(
    source_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        source = service.set_source_status(session, source_id, "archived")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(session, "source_archive", user_id=0, source_id=source.id)
    return {"id": source.id, "status": source.status}


@router.get("/{source_id}/chunks")
def source_chunks(
    source_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        chunks = service.source_chunks(session, source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        {"id": c.id, "content": c.content, "chunk_index": c.chunk_index,
         "article": c.article}
        for c in chunks
    ]


@router.post("/test-retrieval")
def test_retrieval(
    payload: RetrievalQuery,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return service.test_retrieval(session, payload.query, top_k=payload.top_k)