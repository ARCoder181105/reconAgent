"""Shared pytest fixtures.

Provides a temporary in-memory SQLite engine per test so the global
`backend/data/recon.sqlite3` file is never touched by tests.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models  # noqa: F401  (register models on Base.metadata)
from backend.app.db import Base, init_db

MED = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture()
def db_session():
    """Yield a fresh session over an in-memory DB for each test."""
    init_db(MED)
    Session = sessionmaker(bind=MED, autoflush=False, expire_on_commit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        # Reset all tables between tests for isolation.
        Base.metadata.drop_all(bind=MED)
