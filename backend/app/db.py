"""Database engine, session factory, and schema initialization.

Tables mirror `docs/master-design.md` §9 and §9.1. Amounts are stored as
integer paise. Exception governance state is event-sourced; `exceptions.status`
is only a denormalized projection cache.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_engine(db_path: Path | str | None = None):
    """Create a SQLAlchemy engine, ensuring the DB parent dir exists.

    Defaults to the configured DB path. A caller may pass an explicit path
    (e.g. an in-memory or temp DB in tests).
    """
    if db_path is None:
        resolved = settings.resolved_db_path
    else:
        p = Path(db_path)
        resolved = p if p.is_absolute() else Path(settings.repo_root) / p

    if resolved.as_posix() != ":memory:":
        _ensure_parent(resolved)

    return create_engine(
        f"sqlite:///{resolved}",
        connect_args={"check_same_thread": False},
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine_=engine) -> None:
    """Create all tables if they do not exist."""
    # Import models so they register on the metadata before create_all.
    from backend.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine_)


def get_session() -> Session:
    """Dependency: yield a scoped session for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context-manager session that commits on success, rolls back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
