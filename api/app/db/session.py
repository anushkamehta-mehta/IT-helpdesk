"""Database engine and session management."""
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    # Force the MySQL session to UTC so server-side NOW() timestamps are always UTC.
    connect_args = {"init_command": "SET time_zone = '+00:00'"}
    ca = settings.db_ssl_ca_path
    if ca is not None:
        if not ca.is_file():
            raise RuntimeError(f"DB_SSL_CA file not found: {ca}")
        # Encrypted connection that also verifies the server certificate and host name.
        connect_args["ssl"] = {"ca": str(ca), "check_hostname": True}
    return create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
