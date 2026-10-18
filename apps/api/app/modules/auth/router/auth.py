from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users
from apps.api.app.modules.auth.schemas import LoginRequest, TokenResponse, UserOut, UserCreate
from apps.api.app.modules.auth.service import authenticate_user, build_token, create_user
from apps.api.app.modules.auth.deps import get_current_user, get_user_roles, admin_required

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return build_token(user, session)


@router.post("/logout")
def logout():
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(
    user: Users = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
        roles=get_user_roles(session, user),
    )


@router.post("/users", response_model=UserOut, dependencies=[Depends(admin_required)])
def create_new_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
):
    try:
        user = create_user(
            session,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            organization_id=payload.organization_id,
            roles=payload.roles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
        roles=payload.roles,
    )