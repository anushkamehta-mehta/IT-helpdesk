from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_it
from app.models import User
from app.schemas.user import UserBrief

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/it-team", response_model=list[UserBrief])
def list_it_team(db: Session = Depends(get_db), _: User = Depends(require_it)):
    """Active IT team members (for the 'assign to' dropdown)."""
    query = select(User).where(User.role == "it_team", User.is_active.is_(True)).order_by(User.full_name)
    return [UserBrief.model_validate(u) for u in db.scalars(query)]
