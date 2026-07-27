"""Database engine + session helpers.

Usage::

    from openboson.db import init_db, get_session

    engine = init_db()              # creates SQLite file + tables (idempotent)
    with get_session(engine) as s:  # context-managed Session
        ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from openboson.config import settings
from openboson.models import Base


def get_engine(url: str | None = None) -> Engine:
    """Return a SQLAlchemy engine.

    By default uses ``sqlite:///<data_dir>/openboson.db``. Pass ``url`` to
    override (e.g. in-memory ``sqlite:///:memory:`` for tests).
    """
    if url is None:
        url = f"sqlite:///{settings.db_path}"
    # check_same_thread=False: we may use the engine from Qt threads later.
    return create_engine(url, echo=False, future=True, connect_args={"check_same_thread": False})


def init_db(engine: Engine | None = None) -> Engine:
    """Create the engine (if None) and all tables. Idempotent."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def init_db_at(path: Path | str) -> Engine:
    """Convenience for tests: create engine + tables at an explicit path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    return engine


_SessionFactory = None


def get_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def get_session(engine: Engine) -> Iterator[Session]:
    """Generator that yields a Session and closes it. Useful for FastAPI deps."""
    factory = get_sessionmaker(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
