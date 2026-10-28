from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Role = Literal["employee", "it_team", "admin"]


class RegisterRequest(BaseModel):
    full_name: Name
    email: EmailStr
    password: Password


class LoginRequest(BaseModel):
    email: str
    password: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str


class UserOut(UserBrief):
    email: str
    role: str


class AdminUserOut(UserOut):
    is_active: bool
    created_at: datetime


class AdminUserCreate(BaseModel):
    full_name: Name
    email: EmailStr
    password: Password
    role: Role = "employee"


class AdminUserUpdate(BaseModel):
    """Partial update. Omitted fields are left unchanged; password resets it."""

    full_name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None
    role: Role | None = None
    is_active: bool | None = None
