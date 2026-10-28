"""Shared FastAPI dependencies: current user and role checks."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

COOKIE_NAME = "access_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise unauthorized
    payload = decode_access_token(token)
    if not payload:
        raise unauthorized
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError):
        raise unauthorized
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_it(user: User = Depends(get_current_user)) -> User:
    if user.role != "it_team":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "IT team access required")
    return user


def require_employee(user: User = Depends(get_current_user)) -> User:
    if user.role != "employee":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Employee access required")
    return user
