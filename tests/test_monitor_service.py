"""Testes do serviço de orquestração (com providers e canais fakes)."""

from __future__ import annotations

from collections.abc import Sequence

from app.filters.vehicle_filter import VehicleFilter
from app.models.enums import NotificationChannel
from app.models.vehicle import ScrapedVehicle
from app.notifications.base import NotificationMessage, NotificationProvider
from app.notifications.dispatcher import NotificationDispatcher
from app.providers.base import BaseVehicleProvider
from app.services.monitor_service import MonitorService
from app.services.search_service import SearchService


class FakeProvider(BaseVehicleProvider):
    """Provider que retorna anúncios pré-definidos, sem rede."""

    source = "fake"

    def __init__(self, vehicles: Sequence[ScrapedVehicle]) -> None:
        super().__init__()
        self._vehicles = list(vehicles)

    def build_search_urls(self, vehicle_filter):  # pragma: no cover - não usado
        return []

    def get_item_selector(self):  # pragma: no cover - não usado
        return ""

    def parse_item(self, element):  # pragma: no cover - não usado
        return None

    def search(self, vehicle_filter, *, max_results=None):
        return [v for v in self._vehicles if vehicle_filter.matches(v)]


class RecordingNotifier(NotificationProvider):
    channel = NotificationChannel.DISCORD

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[NotificationMessage] = []

    def is_enabled(self) -> bool:
        return True

    def _deliver(self, message: NotificationMessage) -> None:
        self.messages.append(message)


def _scraped(external_id: str, price: float) -> ScrapedVehicle:
    return ScrapedVehicle(
        source="fake",
        external_id=external_id,
        url=f"https://exemplo.com/{external_id}",
        title="Honda Civic",
        brand="Honda",
        model="Civic",
        year=2019,
        price=price,
    )


def _monitor(session, vehicles):
    notifier = RecordingNotifier()
    dispatcher = NotificationDispatcher([notifier], session=session)
    provider = FakeProvider(vehicles)
    return MonitorService(session, providers=[provider], dispatcher=dispatcher), notifier


def test_run_search_persiste_e_notifica(session) -> None:
    monitor, notifier = _monitor(session, [_scraped("1", 95_000)])
    result = monitor.run_search(VehicleFilter(brand="Honda"), notify=True)
    assert result.new_count == 1
    assert result.notifications_sent == 1
    assert len(notifier.messages) == 1


def test_run_search_sem_notify_nao_envia(session) -> None:
    monitor, notifier = _monitor(session, [_scraped("1", 95_000)])
    result = monitor.run_search(VehicleFilter(), notify=False)
    assert result.new_count == 1
    assert notifier.messages == []


def test_segunda_execucao_detecta_queda_e_notifica(session) -> None:
    provider = FakeProvider([_scraped("1", 95_000)])
    notifier = RecordingNotifier()
    dispatcher = NotificationDispatcher([notifier], session=session)
    monitor = MonitorService(session, providers=[provider], dispatcher=dispatcher)

    monitor.run_search(VehicleFilter(), notify=True)
    provider._vehicles = [_scraped("1", 89_000)]
    result = monitor.run_search(VehicleFilter(), notify=True)

    assert result.new_count == 0
    assert result.price_drop_count == 1
    # 1 (novo) + 1 (queda) = 2 mensagens no total
    assert len(notifier.messages) == 2


def test_run_saved_executa_e_marca(session) -> None:
    searches = SearchService(session)
    saved = searches.create("civic", VehicleFilter(brand="Honda"))
    monitor, _ = _monitor(session, [_scraped("1", 95_000)])
    result = monitor.run_saved(saved)
    assert result.new_count == 1
    assert saved.run_count == 1
    assert saved.last_run_at is not None


def test_filtro_aplicado_na_coleta(session) -> None:
    monitor, _ = _monitor(session, [_scraped("1", 95_000)])
    # Filtro de preço máximo exclui o anúncio de 95k.
    result = monitor.run_search(VehicleFilter(price_max=80_000))
    assert result.new_count == 0
