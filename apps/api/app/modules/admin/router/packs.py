from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, PackVersion
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.auth.deps import admin_required
from apps.api.app.modules.admin import service
from apps.api.app.modules.admin.schemas import PackImportRequest, PackStatusRequest

router = APIRouter(prefix="/admin/packs", tags=["admin-packs"])


@router.post("/import")
def import_pack(
    payload: PackImportRequest,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        pack = service.import_pack(session, payload.path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(session, "pack_import", user_id=0,
                 pack_id=pack.id, name=pack.name)
    return service.pack_object(pack, session)


@router.post("")
def create_pack(
    payload: PackImportRequest,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return import_pack(payload, session, _)


@router.get("")
def list_packs(
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return [service.pack_object(p, session) for p in service.list_packs(session)]


@router.get("/{pack_id}")
def get_pack(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    from apps.api.app.modules.core.models import JurisdictionPack
    pack = session.get(JurisdictionPack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")
    return service.pack_object(pack, session)


@router.post("/{pack_id}/validate")
def validate_pack(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        return service.validate_pack(session, pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{pack_id}/activate")
def activate_pack(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        pack = service.set_pack_status(session, pack_id, "active")
    except (KeyError, ValueError) as exc:
        if isinstance(exc, KeyError):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(session, "pack_activate", user_id=0, pack_id=pack.id)
    return service.pack_object(pack, session)


@router.post("/{pack_id}/archive")
def archive_pack(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        pack = service.set_pack_status(session, pack_id, "archived")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(session, "pack_archive", user_id=0, pack_id=pack.id)
    return service.pack_object(pack, session)


@router.get("/{pack_id}/diff")
def pack_diff(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    try:
        return service.pack_diff(session, pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{pack_id}/versions")
def pack_versions(
    pack_id: int,
    session: Session = Depends(get_session),
    _: Users = Depends(admin_required),
):
    return [
        {"id": v.id, "version_number": v.version_number, "status": v.status}
        for v in service.list_pack_versions(session, pack_id)
    ]