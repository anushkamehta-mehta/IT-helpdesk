from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user, require_employee, require_it
from app.models import User
from app.schemas.ticket import CommentCreate, TicketCreate, TicketDetail, TicketOut, TicketUpdate
from app.services import tickets as service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), user: User = Depends(require_employee)):
    return TicketDetail.model_validate(service.create_ticket(db, user, data))


@router.get("", response_model=list[TicketOut])
def list_tickets(
    q: str | None = Query(None, max_length=200),
    status_: Literal["Open", "Assigned", "In Progress", "Closed"] | None = Query(None, alias="status"),
    priority: Literal["Low", "Medium", "High"] | None = None,
    category_id: int | None = None,
    assigned_to: int | None = None,
    unassigned: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Employees see only their own tickets; IT sees all. Same filters for both."""
    tickets = service.list_tickets(
        db, user, q=q, status_=status_, priority=priority,
        category_id=category_id, assigned_to=assigned_to, unassigned=unassigned,
    )
    return [TicketOut.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return TicketDetail.model_validate(service.get_ticket(db, user, ticket_id))


@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db), user: User = Depends(require_it)
):
    return TicketDetail.model_validate(service.update_ticket(db, user, ticket_id, data))


@router.post("/{ticket_id}/comments", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int, data: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return TicketDetail.model_validate(service.add_comment(db, user, ticket_id, data))
