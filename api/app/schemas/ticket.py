from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.user import UserBrief

Priority = Literal["Low", "Medium", "High"]
Status = Literal["Open", "Assigned", "In Progress", "Closed"]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TicketCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
    category_id: int
    priority: Priority = "Medium"


class TicketUpdate(BaseModel):
    """IT-only partial update. Omitted fields are left unchanged."""

    status: Status | None = None
    priority: Priority | None = None
    assigned_to: int | None = None
    resolution_notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)] | None = None


class CommentCreate(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    body: str
    created_at: datetime
    author: UserBrief


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: CategoryOut
    priority: str
    status: str
    creator: UserBrief
    assignee: UserBrief | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class TicketDetail(TicketOut):
    comments: list[CommentOut]
