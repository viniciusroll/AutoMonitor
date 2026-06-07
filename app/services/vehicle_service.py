"""Serviço de persistência de veículos.

Responsável por inserir/atualizar anúncios evitando duplicação (chave
``source`` + ``external_id``), registrar o histórico de preços e
detectar eventos relevantes (novo anúncio e redução de preço).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory
from app.models.vehicle import ScrapedVehicle, Vehicle
from app.utils.logger import get_logger

logger = get_logger("vehicle_service")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PriceDrop:
    """Representa uma redução de preço detectada em um veículo."""

    vehicle: Vehicle
    old_price: float
    new_price: float

    @property
    def difference(self) -> float:
        """Valor absoluto da redução (sempre positivo)."""
        return self.old_price - self.new_price

    @property
    def percent(self) -> float:
        """Redução percentual em relação ao preço anterior."""
        if self.old_price <= 0:
            return 0.0
        return self.difference / self.old_price * 100.0


@dataclass(slots=True)
class SaveReport:
    """Resultado de uma operação de persistência em lote."""

    new_vehicles: list[Vehicle] = field(default_factory=list)
    updated_vehicles: list[Vehicle] = field(default_factory=list)
    price_drops: list[PriceDrop] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.new_vehicles) + len(self.updated_vehicles)


class VehicleService:
    """Casos de uso de persistência e detecção de eventos de veículos."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def save_many(self, scraped: Iterable[ScrapedVehicle]) -> SaveReport:
        """Persiste vários anúncios coletados, retornando os eventos.

        Anúncios inexistentes são inseridos; existentes são atualizados.
        Toda mudança de preço gera um registro em ``price_history`` e,
        quando há queda, um :class:`PriceDrop` no relatório.
        """
        report = SaveReport()
        for item in scraped:
            self._save_one(item, report)
        self._session.flush()
        logger.info(
            f"Persistência: {len(report.new_vehicles)} novos, "
            f"{len(report.updated_vehicles)} atualizados, "
            f"{len(report.price_drops)} reduções de preço."
        )
        return report

    def _save_one(self, item: ScrapedVehicle, report: SaveReport) -> None:
        existing = self._find(item.source, item.external_id)
        if existing is None:
            vehicle = item.to_orm()
            vehicle.first_seen_at = _utcnow()
            vehicle.last_seen_at = _utcnow()
            self._session.add(vehicle)
            self._session.flush()
            if vehicle.price is not None:
                self._record_price(vehicle, vehicle.price)
            report.new_vehicles.append(vehicle)
            return

        drop = self._update_existing(existing, item)
        report.updated_vehicles.append(existing)
        if drop is not None:
            report.price_drops.append(drop)

    def _update_existing(
        self, vehicle: Vehicle, item: ScrapedVehicle
    ) -> PriceDrop | None:
        old_price = vehicle.price
        drop: PriceDrop | None = None

        if item.price is not None and item.price != old_price:
            self._record_price(vehicle, item.price)
            if old_price is not None and item.price < old_price:
                drop = PriceDrop(vehicle, old_price, item.price)
            vehicle.price = item.price

        # Atualiza campos potencialmente voláteis.
        for attr in ("title", "mileage", "city", "state", "photo_count"):
            value = getattr(item, attr, None)
            if value is not None:
                setattr(vehicle, attr, value)
        # ``url`` é um HttpUrl no DTO; persiste-se como string.
        if item.url is not None:
            vehicle.url = str(item.url)

        vehicle.last_seen_at = _utcnow()
        vehicle.is_active = True
        return drop

    def _record_price(self, vehicle: Vehicle, price: float) -> None:
        self._session.add(PriceHistory(vehicle_id=vehicle.id, price=price))

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def _find(self, source: str, external_id: str) -> Vehicle | None:
        stmt = select(Vehicle).where(
            Vehicle.source == source, Vehicle.external_id == external_id
        )
        return self._session.scalars(stmt).first()

    def list_vehicles(
        self, *, source: str | None = None, limit: int | None = None
    ) -> Sequence[Vehicle]:
        """Lista veículos persistidos, opcionalmente por fonte."""
        stmt = select(Vehicle).order_by(Vehicle.collected_at.desc())
        if source:
            stmt = stmt.where(Vehicle.source == source)
        if limit:
            stmt = stmt.limit(limit)
        return self._session.scalars(stmt).all()
