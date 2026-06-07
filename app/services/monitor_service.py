"""Serviço de orquestração de busca e monitoramento.

Une providers, persistência e notificações:

- :meth:`MonitorService.run_search` executa uma busca pontual.
- :meth:`MonitorService.run_saved` executa uma busca salva e dispara
  alertas de novos anúncios e reduções de preço.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.filters.vehicle_filter import VehicleFilter
from app.models.enums import NotificationEvent
from app.models.search import Search
from app.models.vehicle import ScrapedVehicle, Vehicle
from app.notifications.dispatcher import NotificationDispatcher
from app.providers.base import BaseVehicleProvider
from app.providers.registry import get_providers
from app.services.search_service import SearchService
from app.services.vehicle_service import SaveReport, VehicleService
from app.utils.logger import get_logger

logger = get_logger("monitor_service")


@dataclass(slots=True)
class RunResult:
    """Resultado consolidado da execução de uma busca."""

    scraped: list[ScrapedVehicle] = field(default_factory=list)
    report: SaveReport | None = None
    notifications_sent: int = 0

    @property
    def new_count(self) -> int:
        return len(self.report.new_vehicles) if self.report else 0

    @property
    def price_drop_count(self) -> int:
        return len(self.report.price_drops) if self.report else 0


class MonitorService:
    """Orquestra coleta, persistência e notificações."""

    def __init__(
        self,
        session: Session,
        *,
        providers: Sequence[BaseVehicleProvider] | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self._session = session
        self._providers = list(providers) if providers is not None else None
        self._vehicles = VehicleService(session)
        self._searches = SearchService(session)
        self._dispatcher = dispatcher or NotificationDispatcher(session=session)

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------
    def collect(
        self,
        vehicle_filter: VehicleFilter,
        *,
        sources: list[str] | None = None,
        max_results: int | None = None,
    ) -> list[ScrapedVehicle]:
        """Executa a coleta em todos os providers selecionados."""
        providers = self._resolve_providers(sources)
        collected: list[ScrapedVehicle] = []
        for provider in providers:
            try:
                collected.extend(
                    provider.search(vehicle_filter, max_results=max_results)
                )
            except Exception as exc:
                logger.error(f"Provider {provider.source} falhou: {exc}")
        logger.info(f"Coleta total: {len(collected)} anúncios.")
        return collected

    def run_search(
        self,
        vehicle_filter: VehicleFilter,
        *,
        sources: list[str] | None = None,
        max_results: int | None = None,
        notify: bool = False,
    ) -> RunResult:
        """Executa uma busca pontual: coleta, persiste e (opcional) notifica."""
        scraped = self.collect(
            vehicle_filter, sources=sources, max_results=max_results
        )
        report = self._vehicles.save_many(scraped)
        sent = self._notify(report) if notify else 0
        return RunResult(scraped=scraped, report=report, notifications_sent=sent)

    def run_saved(
        self, search: Search, *, sources: list[str] | None = None
    ) -> RunResult:
        """Executa uma busca salva e dispara as notificações pertinentes."""
        vehicle_filter = self._searches.filter_of(search)
        logger.info(f"Executando busca salva {search.name!r}.")
        result = self.run_search(
            vehicle_filter, sources=sources, notify=True
        )
        self._searches.mark_run(search)
        return result

    # ------------------------------------------------------------------
    # Notificações
    # ------------------------------------------------------------------
    def _notify(self, report: SaveReport) -> int:
        sent = 0
        for vehicle in report.new_vehicles:
            sent += self._dispatcher.notify(NotificationEvent.NEW_VEHICLE, vehicle)
        for drop in report.price_drops:
            extra = (
                f"De R$ {drop.old_price:,.0f} para R$ {drop.new_price:,.0f} "
                f"(-{drop.percent:.1f}%)"
            ).replace(",", ".")
            sent += self._dispatcher.notify(
                NotificationEvent.PRICE_DROP, drop.vehicle, extra=extra
            )
        return sent

    # ------------------------------------------------------------------
    def _resolve_providers(
        self, sources: list[str] | None
    ) -> list[BaseVehicleProvider]:
        if self._providers is not None:
            if sources is None:
                return self._providers
            return [p for p in self._providers if p.source in sources]
        return get_providers(sources)
