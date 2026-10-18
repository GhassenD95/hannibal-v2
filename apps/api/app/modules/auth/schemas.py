from typing import Optional, List
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: Optional[str] = None
    organization_id: Optional[int] = None
    roles: List[str] = []


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    organization_id: Optional[int] = None
    roles: List[str] = []


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    organization_id: Optional[int] = None
    roles: List[str] = ["viewer"]