"""Testes do serviço de estatísticas."""

from __future__ import annotations

from app.filters.vehicle_filter import VehicleFilter
from app.services.search_service import SearchService
from app.services.stats_service import StatsService
from app.services.vehicle_service import VehicleService


def test_stats_banco_vazio(session) -> None:
    stats = StatsService(session).compute()
    assert stats.total_vehicles == 0
    assert stats.avg_price is None
    assert stats.by_source == {}


def test_stats_agrega_veiculos_e_precos(session, scraped_factory) -> None:
    vehicles = VehicleService(session)
    vehicles.save_many(
        [
            scraped_factory(external_id="1", source="webmotors", price=90_000),
            scraped_factory(external_id="2", source="webmotors", price=110_000),
        ]
    )
    SearchService(session).create("c", VehicleFilter(brand="Honda"))

    stats = StatsService(session).compute()
    assert stats.total_vehicles == 2
    assert stats.active_vehicles == 2
    assert stats.min_price == 90_000
    assert stats.max_price == 110_000
    assert stats.avg_price == 100_000
    assert stats.by_source == {"webmotors": 2}
    assert stats.total_searches == 1
    assert stats.active_searches == 1
