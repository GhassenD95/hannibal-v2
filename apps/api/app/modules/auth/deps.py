"""FastAPI dependencies: current user, role checks, org scoping."""

from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, Role, UserRole

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> Users:
    from apps.api.app.modules.auth.security import decode_token

    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = session.get(Users, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or unknown user"
        )
    return user


def get_user_roles(session: Session, user: Users) -> List[str]:
    statement = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == user.id
    )
    return list(session.exec(statement).all())


def role_required(*required: str):
    def checker(
        user: Users = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> Users:
        roles = get_user_roles(session, user)
        if user.is_superuser:
            return user
        if not set(required).intersection(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role(s): {', '.join(required)}",
            )
        return user

    return checker


admin_required = role_required("admin")


def current_user_org(user: Users = Depends(get_current_user)) -> Optional[int]:
    if user.is_superuser:
        return None  # None = no org filter (see contract_org_filter)
    return user.organization_id


def contract_org_filter(user: Users, organization_id: Optional[int]) -> None:
    """Ensure an org-scoped user may only touch their own organization's data."""
    if user.is_superuser:
        return
    if organization_id != user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied"
        )