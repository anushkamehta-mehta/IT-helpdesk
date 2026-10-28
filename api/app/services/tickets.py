"""Ticket business rules: visibility, workflow transitions, comments."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Comment, Ticket, User
from app.schemas.ticket import CommentCreate, TicketCreate, TicketUpdate

# Workflow: Open -> Assigned -> In Progress -> Closed. A ticket may also be closed
# directly (e.g. duplicate or resolved on first contact); closing needs resolution notes.
ALLOWED_TRANSITIONS = {
    "Open": {"Assigned", "Closed"},
    "Assigned": {"In Progress", "Closed"},
    "In Progress": {"Closed"},
    "Closed": set(),
}


def _base_query():
    return select(Ticket).options(
        joinedload(Ticket.category), joinedload(Ticket.creator), joinedload(Ticket.assignee)
    )


def list_tickets(
    db: Session,
    user: User,
    *,
    q: str | None = None,
    status_: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    assigned_to: int | None = None,
    unassigned: bool = False,
) -> list[Ticket]:
    query = _base_query()
    if user.role == "employee":
        query = query.where(Ticket.created_by == user.id)
    if q:
        q = q.strip()
        conditions = [Ticket.title.contains(q, autoescape=True), Ticket.description.contains(q, autoescape=True)]
        if q.isdigit():
            conditions.append(Ticket.id == int(q))
        query = query.where(or_(*conditions))
    if status_:
        query = query.where(Ticket.status == status_)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category_id:
        query = query.where(Ticket.category_id == category_id)
    if unassigned:
        query = query.where(Ticket.assigned_to.is_(None))
    elif assigned_to:
        query = query.where(Ticket.assigned_to == assigned_to)
    query = query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    return list(db.scalars(query).unique())


def get_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    query = (
        _base_query()
        .options(selectinload(Ticket.comments).joinedload(Comment.author))
        .where(Ticket.id == ticket_id)
        # Always refresh from the DB so a re-read after commit never returns stale relationships.
        .execution_options(populate_existing=True)
    )
    ticket = db.scalars(query).unique().first()
    # Employees get 404 (not 403) for other people's tickets so ids can't be probed.
    if ticket is None or (user.role == "employee" and ticket.created_by != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


def create_ticket(db: Session, user: User, data: TicketCreate) -> Ticket:
    if db.get(Category, data.category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category")
    ticket = Ticket(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        status="Open",
        created_by=user.id,
    )
    db.add(ticket)
    db.commit()
    return get_ticket(db, user, ticket.id)


IT_ONLY_FIELDS = ("status", "assigned_to", "resolution_notes")


def update_ticket(db: Session, user: User, ticket_id: int, data: TicketUpdate) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)  # enforces employee ownership
    if user.role != "it_team" and any(getattr(data, f) is not None for f in IT_ONLY_FIELDS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the IT team can change status, assignee or resolution notes")
    if ticket.status == "Closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Closed tickets cannot be modified")

    if data.title is not None:
        ticket.title = data.title
    if data.description is not None:
        ticket.description = data.description
    if data.category_id is not None:
        if db.get(Category, data.category_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category")
        ticket.category_id = data.category_id

    if data.priority is not None:
        ticket.priority = data.priority

    if data.resolution_notes is not None:
        ticket.resolution_notes = data.resolution_notes or None

    if data.assigned_to is not None:
        assignee = db.get(User, data.assigned_to)
        if assignee is None or assignee.role != "it_team" or not assignee.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assignee must be an active IT team member")
        ticket.assigned_to = assignee.id
        if ticket.status == "Open" and data.status is None:
            ticket.status = "Assigned"

    if data.status is not None and data.status != ticket.status:
        if data.status not in ALLOWED_TRANSITIONS[ticket.status]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Cannot change status from {ticket.status} to {data.status}",
            )
        if data.status in ("Assigned", "In Progress") and ticket.assigned_to is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assign the ticket to someone first")
        if data.status == "Closed":
            if not (ticket.resolution_notes or "").strip():
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Resolution notes are required to close a ticket")
            ticket.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        ticket.status = data.status

    db.commit()
    return get_ticket(db, user, ticket_id)


def delete_ticket(db: Session, user: User, ticket_id: int) -> None:
    ticket = get_ticket(db, user, ticket_id)  # enforces employee ownership
    db.delete(ticket)  # comments go with it (ORM cascade + ON DELETE CASCADE)
    db.commit()


def add_comment(db: Session, user: User, ticket_id: int, data: CommentCreate) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)  # enforces employee ownership
    if ticket.status == "Closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot comment on a closed ticket")
    db.add(Comment(ticket_id=ticket.id, author_id=user.id, body=data.body))
    db.commit()
    return get_ticket(db, user, ticket_id)
