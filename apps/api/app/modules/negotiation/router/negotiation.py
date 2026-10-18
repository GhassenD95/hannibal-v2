from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users
from apps.api.app.modules.auth.deps import get_current_user
from apps.api.app.modules.negotiation import service
from apps.api.app.modules.contracts.service import OrgPermissionError, NotFoundError

router = APIRouter(prefix="/contracts", tags=["negotiation"])


class CreateNegotiationRequest(BaseModel):
    section_id: int
    counterparty_clause: str
    original_clause_id: Optional[int] = None


class DecisionRequest(BaseModel):
    decision: str


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (OrgPermissionError, service.NegotiationError, NotFoundError)):
        code = 403 if isinstance(exc, OrgPermissionError) else 400
        status = 403 if isinstance(exc, OrgPermissionError) else 404 if isinstance(exc, NotFoundError) else 400
        return HTTPException(status_code=status, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/{contract_id}/negotiations")
def list_negotiations(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        return service.list_negotiations(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{contract_id}/negotiations")
def create_negotiation(
    contract_id: int,
    payload: CreateNegotiationRequest,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        return service.create_negotiation(
            session, user, contract_id, payload.section_id,
            payload.counterparty_clause, payload.original_clause_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{contract_id}/negotiations/{item_id}/analyze")
async def analyze_negotiation(
    contract_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        return await service.analyze_negotiation(session, user, contract_id, item_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{contract_id}/negotiations/{item_id}/propose")
async def propose_negotiation(
    contract_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        return await service.propose_negotiation(session, user, contract_id, item_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{contract_id}/negotiations/{item_id}/decide")
async def decide_negotiation(
    contract_id: int,
    item_id: int,
    payload: DecisionRequest,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        return service.decide_negotiation(session, user, contract_id, item_id,
                                          payload.decision)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc