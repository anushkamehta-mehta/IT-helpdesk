"""Shared FastAPI dependencies: current user and role checks."""
import time

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.db.session import get_db
from app.models import User

COOKIE_NAME = "access_token"


def set_auth_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id, user.role),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # No cookie: never logged in here, logged out (possibly in another tab), or the cookie expired.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "You are logged out. Please log in again.")
    expired = HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again.")
    payload = decode_access_token(token)
    if not payload:
        raise expired
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError):
        raise expired
    if user is None or not user.is_active:
        raise expired
    # Sliding session: once less than half the lifetime is left, issue a fresh token,
    # so people who keep working are not logged out mid-task.
    if payload.get("exp", 0) - time.time() < get_settings().jwt_expire_minutes * 30:
        set_auth_cookie(response, user)
    return user


def require_it(user: User = Depends(get_current_user)) -> User:
    if user.role != "it_team":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "IT team access required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def require_employee(user: User = Depends(get_current_user)) -> User:
    if user.role != "employee":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Employee access required")
    return user
