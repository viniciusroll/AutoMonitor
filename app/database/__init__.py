"""Infraestrutura de persistência (SQLAlchemy + SQLite)."""

from __future__ import annotations

from app.database.base import (
    Base,
    SessionLocal,
    engine,
    get_session,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_session",
    "init_db",
    "session_scope",
]
