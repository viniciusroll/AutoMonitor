"""Modelo de busca salva (conjunto de filtros monitorado)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Search(Base):
    """Uma busca nomeada e persistida, com seus filtros e metadados.

    Os filtros são armazenados como JSON, permitindo evoluir os campos
    de filtragem sem alterar o schema.
    """

    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Search id={self.id} name={self.name!r} active={self.is_active}>"
