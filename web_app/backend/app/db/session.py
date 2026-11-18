"""Engine and session factory for the Postgres-backed P0.5 store.

One process-wide `Engine` (SQLAlchemy pools connections itself, so this
is safe across threads and across multiple uvicorn workers each with
their own process). `session_scope()` is the only way code should touch
the database: it always commits or rolls back, never leaves a
transaction open.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed on success."""
    with session_scope() as session:
        yield session


def reset_engine_cache() -> None:
    """Test-only: forces a fresh engine/session factory after settings change."""
    get_engine.cache_clear()
    get_session_factory.cache_clear()
