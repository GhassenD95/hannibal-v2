from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users
from apps.api.app.modules.auth.deps import admin_required
from apps.api.app.modules.admin import service
from apps.api.app.modules.admin.schemas import ClauseCreate

router = APIRouter(prefix="/admin/clauses", tags=["admin-clauses"])


@router.get("")
def list_clauses(
    contract_type: str = None,
    jurisdiction: str = None,
    status: str = None,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return [
        {"id": c.id, "title": c.title, "contract_type": c.contract_type,
         "clause_type": c.clause_type, "status": c.status, "version": c.version}
        for c in service.list_clauses(session, contract_type, jurisdiction, status)
    ]


@router.post("")
def create_clause(
    payload: ClauseCreate,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    clause = service.create_clause(session, payload.model_dump())
    return {"id": clause.id, "title": clause.title, "status": clause.status}


@router.post("/{clause_id}/archive")
def archive_clause(
    clause_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    from apps.api.app.modules.core.models import Clause
    clause = session.get(Clause, clause_id)
    if clause is None:
        raise HTTPException(status_code=404, detail="Clause not found")
    clause.status = "archived"
    session.add(clause)
    session.commit()
    return {"id": clause.id, "status": clause.status}