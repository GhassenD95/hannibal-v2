"""Auth business logic: login, user creation, role assignment."""

from typing import Optional, List

from sqlmodel import Session, select

from apps.api.app.modules.core.models import Users, Role, UserRole, Organizations
from apps.api.app.modules.auth.security import get_password_hash, verify_password, create_access_token
from apps.api.app.modules.auth.deps import get_user_roles


def get_user_by_email(session: Session, email: str) -> Optional[Users]:
    statement = select(Users).where(Users.email == email)
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[Users]:
    return session.get(Users, user_id)


def authenticate_user(session: Session, email: str, password: str) -> Optional[Users]:
    user = get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def build_token(user: Users, session: Session) -> dict:
    roles = get_user_roles(session, user)
    token = create_access_token({"sub": str(user.id), "org": user.organization_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.organization_id,
        "roles": roles,
    }


def create_user(
    session: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    organization_id: Optional[int] = None,
    roles: Optional[List[str]] = None,
) -> Users:
    if get_user_by_email(session, email):
        raise ValueError("User with this email already exists")
    if organization_id is not None:
        org = session.get(Organizations, organization_id)
        if not org:
            raise ValueError("Unknown organization")
    user = Users(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        organization_id=organization_id,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for role_name in roles or ["viewer"]:
        role = session.exec(select(Role).where(Role.name == role_name)).first()
        if role:
            session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    session.refresh(user)
    return user