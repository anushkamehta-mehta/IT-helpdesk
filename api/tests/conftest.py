"""Test setup: runs the API against an in-memory SQLite database (no MySQL needed)."""
import os

# Must be set before the app is imported.
os.environ.update(
    DB_USER="test", DB_PASSWORD="test", JWT_SECRET="test-secret-test-secret-test-secret", COOKIE_SECURE="false"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Category, User


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        db.add(Category(name="Hardware"))
        db.add(User(full_name="Ivan IT", email="ivan@acme.com", password_hash=hash_password("password123"), role="it_team"))
        db.add(User(full_name="Priya IT", email="priya@acme.com", password_hash=hash_password("password123"), role="it_team"))
        db.commit()
    yield factory
    engine.dispose()


@pytest.fixture()
def make_client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    def _make():
        return TestClient(app, headers={"X-Requested-With": "fetch"})

    yield _make
    app.dependency_overrides.clear()
