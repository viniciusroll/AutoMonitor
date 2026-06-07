"""Modelo de veículo (ORM) e DTO de coleta (Pydantic).

- :class:`Vehicle` é a entidade persistida no banco.
- :class:`ScrapedVehicle` é o objeto de transferência retornado pelos
  providers, desacoplando a coleta da persistência.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import FuelType, SellerType, TransmissionType

if TYPE_CHECKING:
    from app.models.price_history import PriceHistory


def _utcnow() -> datetime:
    """Retorna o instante atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


class Vehicle(Base):
    """Anúncio de veículo persistido.

    A unicidade lógica de um anúncio é dada pelo par
    ``(source, external_id)``, o que evita duplicação entre coletas.
    """

    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação / origem
    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    url: Mapped[str] = mapped_column(Text)

    # Descrição do veículo
    title: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(80), index=True, default=None)
    model: Mapped[str | None] = mapped_column(String(120), index=True, default=None)
    version: Mapped[str | None] = mapped_column(String(160), default=None)
    year: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    mileage: Mapped[int | None] = mapped_column(Integer, default=None)
    price: Mapped[float | None] = mapped_column(Float, index=True, default=None)
    fuel: Mapped[str | None] = mapped_column(String(20), default=None)
    transmission: Mapped[str | None] = mapped_column(String(20), default=None)
    color: Mapped[str | None] = mapped_column(String(40), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Localização
    city: Mapped[str | None] = mapped_column(String(120), index=True, default=None)
    state: Mapped[str | None] = mapped_column(String(2), index=True, default=None)

    # Vendedor / mídia
    seller_name: Mapped[str | None] = mapped_column(String(160), default=None)
    seller_type: Mapped[str] = mapped_column(
        String(20), default=SellerType.DESCONHECIDO.value
    )
    photo_count: Mapped[int] = mapped_column(Integer, default=0)

    # Datas
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Estado
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relacionamentos
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="PriceHistory.recorded_at",
    )

    def __repr__(self) -> str:  # pragma: no cover - representação
        return (
            f"<Vehicle id={self.id} source={self.source!r} "
            f"title={self.title!r} price={self.price!r}>"
        )


class ScrapedVehicle(BaseModel):
    """DTO de um anúncio recém-coletado por um provider.

    Independente do ORM: validado e normalizado antes da persistência.
    """

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    source: str
    external_id: str
    url: HttpUrl
    title: str

    brand: str | None = None
    model: str | None = None
    version: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    mileage: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    fuel: FuelType = FuelType.DESCONHECIDO
    transmission: TransmissionType = TransmissionType.DESCONHECIDO
    color: str | None = None
    description: str | None = None

    city: str | None = None
    state: str | None = None

    seller_name: str | None = None
    seller_type: SellerType = SellerType.DESCONHECIDO
    photo_count: int = Field(default=0, ge=0)

    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=_utcnow)

    @field_validator("state")
    @classmethod
    def _normalize_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None

    def to_orm(self) -> Vehicle:
        """Converte o DTO em uma instância ORM :class:`Vehicle`."""
        return Vehicle(
            source=self.source,
            external_id=self.external_id,
            url=str(self.url),
            title=self.title,
            brand=self.brand,
            model=self.model,
            version=self.version,
            year=self.year,
            mileage=self.mileage,
            price=self.price,
            fuel=self.fuel if isinstance(self.fuel, str) else self.fuel.value,
            transmission=(
                self.transmission
                if isinstance(self.transmission, str)
                else self.transmission.value
            ),
            color=self.color,
            description=self.description,
            city=self.city,
            state=self.state,
            seller_name=self.seller_name,
            seller_type=(
                self.seller_type
                if isinstance(self.seller_type, str)
                else self.seller_type.value
            ),
            photo_count=self.photo_count,
            published_at=self.published_at,
            collected_at=self.collected_at,
        )
