"""Ticket business rules: visibility, workflow transitions, comments."""
from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Comment, Ticket, User
from app.schemas.ticket import CommentCreate, TicketCreate, TicketUpdate
from app.services import notifications

# Workflow: Open -> Assigned -> In Progress / On Hold -> Resolved -> Closed.
# * Assigning a ticket (or reassigning it to someone else) always sets it to Assigned.
# * IT moves it between In Progress, On Hold and Resolved; resolving needs resolution notes.
# * Only the employee who raised it can close it, or send a Resolved ticket back with a comment.
IT_TRANSITIONS = {
    "Open": set(),  # assign it first
    "Assigned": {"In Progress", "On Hold", "Resolved"},
    "In Progress": {"On Hold", "Resolved"},
    "On Hold": {"In Progress", "Resolved"},
    "Resolved": {"In Progress"},
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


def update_ticket(
    db: Session, user: User, ticket_id: int, data: TicketUpdate, background_tasks: BackgroundTasks | None = None
) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)  # enforces employee ownership
    if user.role != "it_team" and any(getattr(data, f) is not None for f in IT_ONLY_FIELDS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the IT team can change status, assignee or resolution notes")
    if ticket.status == "Closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Closed tickets cannot be modified")
    previous_status = ticket.status

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
        if assignee.id != ticket.assigned_to:
            ticket.assigned_to = assignee.id
            ticket.status = "Assigned"

    if data.status is not None and data.status != ticket.status:
        if data.status not in IT_TRANSITIONS[ticket.status]:
            hint = " (assign it to someone first)" if ticket.status == "Open" else ""
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Cannot change status from {ticket.status} to {data.status}{hint}",
            )
        if data.status == "Resolved" and not (ticket.resolution_notes or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Resolution notes are required to resolve a ticket")
        ticket.status = data.status

    db.commit()
    ticket = get_ticket(db, user, ticket_id)
    # Tell the requester (on every move into Resolved, including after they asked for changes).
    if data.status == "Resolved" and previous_status != "Resolved" and background_tasks is not None:
        background_tasks.add_task(notifications.send_email, *notifications.ticket_resolved_email(ticket))
    return ticket


def _get_own_open_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)  # enforces employee ownership
    if ticket.created_by != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the employee who raised the ticket can do this")
    if ticket.status == "Closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket is already closed")
    return ticket


def close_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    ticket = _get_own_open_ticket(db, user, ticket_id)
    ticket.status = "Closed"
    ticket.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return get_ticket(db, user, ticket_id)


def reopen_ticket(db: Session, user: User, ticket_id: int, data: CommentCreate) -> Ticket:
    ticket = _get_own_open_ticket(db, user, ticket_id)
    if ticket.status != "Resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a resolved ticket can be sent back for changes")
    ticket.status = "In Progress"
    db.add(Comment(ticket_id=ticket.id, author_id=user.id, body=data.body))
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
