from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, EvaluationRun
from apps.api.app.modules.auth.deps import get_current_user, admin_required
from apps.api.app.modules.evaluation import service as evaluation

router = APIRouter(prefix="/admin/evaluation", tags=["evaluation"])


@router.get("/fixtures")
def list_fixtures(
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
    _admin: Users = Depends(admin_required),
):
    return evaluation.all_fixtures(session)


@router.post("/run")
async def run_evaluation(
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
    _admin: Users = Depends(admin_required),
):
    try:
        return await evaluation.run_evaluation(session, user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def list_runs(
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
    _admin: Users = Depends(admin_required),
):
    runs = session.exec(select(EvaluationRun).order_by(
        EvaluationRun.id.desc())).all()
    return [
        {
            "id": run.id,
            "status": run.status,
            "total_fixtures": run.total_fixtures,
            "metrics": run.metrics,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat(),
        }
        for run in runs
    ]