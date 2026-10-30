"""Database engine and session management."""
import ssl
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
    # Encrypted connection that also verifies the server certificate and host name.
    if settings.db_ssl_ca_pem:
        connect_args["ssl"] = ssl.create_default_context(cadata=settings.db_ssl_ca_pem)
    elif (ca := settings.db_ssl_ca_path) is not None:
        if not ca.is_file():
            raise RuntimeError(f"DB_SSL_CA file not found: {ca}")
        connect_args["ssl"] = ssl.create_default_context(cafile=str(ca))
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
