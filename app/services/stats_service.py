"""Serviço de estatísticas agregadas do banco de dados."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.price_history import PriceHistory
from app.models.search import Search
from app.models.vehicle import Vehicle


@dataclass(slots=True)
class Stats:
    """Resumo estatístico do estado atual do banco."""

    total_vehicles: int = 0
    active_vehicles: int = 0
    total_searches: int = 0
    active_searches: int = 0
    total_notifications: int = 0
    total_price_records: int = 0
    avg_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    by_source: dict[str, int] = field(default_factory=dict)


class StatsService:
    """Calcula métricas agregadas sobre os dados coletados."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def compute(self) -> Stats:
        """Calcula e retorna o resumo estatístico atual."""
        session = self._session
        stats = Stats()

        stats.total_vehicles = self._scalar(select(func.count(Vehicle.id)))
        stats.active_vehicles = self._scalar(
            select(func.count(Vehicle.id)).where(Vehicle.is_active.is_(True))
        )
        stats.total_searches = self._scalar(select(func.count(Search.id)))
        stats.active_searches = self._scalar(
            select(func.count(Search.id)).where(Search.is_active.is_(True))
        )
        stats.total_notifications = self._scalar(
            select(func.count(Notification.id))
        )
        stats.total_price_records = self._scalar(
            select(func.count(PriceHistory.id))
        )

        stats.avg_price = session.scalar(select(func.avg(Vehicle.price)))
        stats.min_price = session.scalar(select(func.min(Vehicle.price)))
        stats.max_price = session.scalar(select(func.max(Vehicle.price)))

        rows = session.execute(
            select(Vehicle.source, func.count(Vehicle.id)).group_by(Vehicle.source)
        ).all()
        stats.by_source = {source: count for source, count in rows}
        return stats

    def _scalar(self, stmt) -> int:  # noqa: ANN001 - statement do SQLAlchemy
        return int(self._session.scalar(stmt) or 0)
