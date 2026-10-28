"""Admin-only user management: create accounts with any role, edit, deactivate, delete."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.dependencies import require_admin
from app.models import Comment, Ticket, User
from app.schemas.user import AdminUserCreate, AdminUserOut, AdminUserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"])

EMAIL_TAKEN = "An account with this email already exists"


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # unique email race
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)


@router.get("", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [AdminUserOut.model_validate(u) for u in db.scalars(select(User).order_by(User.role, User.full_name))]


@router.post("", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: AdminUserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    email = data.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    user = User(full_name=data.full_name, email=email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    _commit(db)
    return AdminUserOut.model_validate(user)


@router.patch("/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int, data: AdminUserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = _get_user(db, user_id)
    # Stops the last admin from locking everyone (including themselves) out.
    if user.id == admin.id and ((data.role and data.role != "admin") or data.is_active is False):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "You cannot remove your own admin access")

    if data.email is not None:
        email = data.email.strip().lower()
        if email != user.email and db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
        user.email = email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    _commit(db)
    return AdminUserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_user(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "You cannot delete your own account")
    has_history = db.scalar(
        select(
            exists().where(or_(Ticket.created_by == user.id, Ticket.assigned_to == user.id))
            | exists().where(Comment.author_id == user.id)
        )
    )
    if has_history:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This user has tickets or comments. Deactivate the account instead."
        )
    db.delete(user)
    db.commit()
