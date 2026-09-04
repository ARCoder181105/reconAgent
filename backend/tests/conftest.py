"""Shared pytest fixtures.

Provides a temporary in-memory SQLite engine per test so the global
`backend/data/recon.sqlite3` file is never touched by tests.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from backend.app import models  # noqa: F401  (register models on Base.metadata)
from backend.app.db import Base, get_session, init_db
from backend.app.main import app

# Shared in-memory engine with StaticPool so the TestClient thread sees the same DB.
_MED = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(bind=_MED, autoflush=False, expire_on_commit=False)


def _override_session():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


# Wire the override once at import time (same pattern as test_main.py).
app.dependency_overrides[get_session] = _override_session


@pytest.fixture(autouse=True)
def _fresh_db():
    """Create tables before each test, drop after."""
    init_db(_MED)
    yield
    Base.metadata.drop_all(bind=_MED)


@pytest.fixture()
def client():
    """Starlette TestClient wired to the FastAPI app with in-memory DB."""
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Yield a fresh session over the in-memory DB for model-level tests."""
    init_db(_MED)
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=_MED)
