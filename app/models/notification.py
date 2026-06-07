"""Modelo de registro de notificações enviadas (auditoria)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """Auditoria de uma notificação disparada por algum evento."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), index=True, default=None
    )
    channel: Mapped[str] = mapped_column(String(20), index=True)
    event: Mapped[str] = mapped_column(String(30), index=True)
    message: Mapped[str] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Notification channel={self.channel!r} event={self.event!r} "
            f"success={self.success}>"
        )
