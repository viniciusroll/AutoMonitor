"""Serviço de buscas salvas (conjuntos de filtros monitorados)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import VehicleMonitorError
from app.filters.vehicle_filter import VehicleFilter
from app.models.search import Search
from app.utils.logger import get_logger

logger = get_logger("search_service")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SearchService:
    """CRUD e ciclo de vida das buscas salvas."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, name: str, vehicle_filter: VehicleFilter) -> Search:
        """Cria uma busca salva (ou atualiza os filtros, se já existir)."""
        existing = self.get(name)
        if existing is not None:
            existing.filters = vehicle_filter.to_dict()
            existing.is_active = True
            logger.info(f"Busca {name!r} atualizada.")
            return existing
        search = Search(name=name, filters=vehicle_filter.to_dict())
        self._session.add(search)
        self._session.flush()
        logger.info(f"Busca {name!r} criada.")
        return search

    def get(self, name: str) -> Search | None:
        """Recupera uma busca pelo nome."""
        stmt = select(Search).where(Search.name == name)
        return self._session.scalars(stmt).first()

    def list_active(self) -> Sequence[Search]:
        """Lista todas as buscas ativas."""
        stmt = select(Search).where(Search.is_active.is_(True))
        return self._session.scalars(stmt).all()

    def list_all(self) -> Sequence[Search]:
        """Lista todas as buscas."""
        return self._session.scalars(select(Search)).all()

    def filter_of(self, search: Search) -> VehicleFilter:
        """Reconstrói o :class:`VehicleFilter` de uma busca salva."""
        return VehicleFilter.from_dict(search.filters)

    def mark_run(self, search: Search) -> None:
        """Registra que a busca foi executada (timestamp + contador)."""
        search.last_run_at = _utcnow()
        search.run_count += 1

    def deactivate(self, name: str) -> None:
        """Desativa uma busca salva."""
        search = self.get(name)
        if search is None:
            raise VehicleMonitorError(f"Busca {name!r} não encontrada.")
        search.is_active = False
        logger.info(f"Busca {name!r} desativada.")
