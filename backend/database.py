"""
SQLite database setup via SQLModel / SQLAlchemy.

Creates the engine, initialises tables on startup, and provides a
session factory used by API routes and the scheduler.

Usage:
    from backend.database import get_session, init_db

    # At startup:
    init_db()

    # In a FastAPI route (dependency injection):
    def my_route(session: Session = Depends(get_session)):
        ...

    # In the scheduler (direct call):
    with get_session_ctx() as session:
        session.add(...)
        session.commit()
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

# Import all models so SQLModel sees them before create_all()
from backend.models.readings import (  # noqa: F401
    ChargingSession,
    DailySummary,
    Integration,
    Reading,
)

_engine = None


def _default_db_url() -> str:
    import os
    from pathlib import Path
    data_dir = Path(os.environ.get("HEMS_DATA_DIR", "."))
    return f"sqlite:///{data_dir / 'hems.db'}"


def get_engine(db_url: str = ""):
    """Return (and lazily create) the SQLAlchemy engine.

    Uses check_same_thread=False for SQLite so FastAPI's async workers
    can share the connection safely via session-per-request pattern.
    """
    global _engine
    if _engine is None:
        url = db_url or _default_db_url()
        connect_args = {"check_same_thread": False}
        _engine = create_engine(url, connect_args=connect_args)
    return _engine


def init_db(db_url: str = "") -> None:
    """Create all tables if they do not exist yet.

    Safe to call on every startup — SQLModel/SQLAlchemy skips tables
    that already exist (does not migrate or drop data).
    """
    engine = get_engine(db_url)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    with Session(get_engine()) as session:
        yield session


@contextmanager
def get_session_ctx() -> Generator[Session, None, None]:
    """Context manager for use outside FastAPI (e.g. the scheduler)."""
    with Session(get_engine()) as session:
        yield session
