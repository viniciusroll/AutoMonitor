"""Modelo de histórico de preços de um veículo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PriceHistory(Base):
    """Registro de um preço observado para um veículo em um instante."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, index=True
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle", back_populates="price_history"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PriceHistory vehicle_id={self.vehicle_id} "
            f"price={self.price!r} at={self.recorded_at!r}>"
        )
