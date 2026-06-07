"""Testes do serviço de buscas salvas."""

from __future__ import annotations

import pytest

from app.exceptions import VehicleMonitorError
from app.filters.vehicle_filter import VehicleFilter
from app.services.search_service import SearchService


def test_cria_e_recupera_busca(session) -> None:
    service = SearchService(session)
    service.create("civic", VehicleFilter(brand="Honda", model="Civic"))
    recuperada = service.get("civic")
    assert recuperada is not None
    assert recuperada.filters["brand"] == "Honda"


def test_criar_busca_existente_atualiza_filtros(session) -> None:
    service = SearchService(session)
    service.create("civic", VehicleFilter(brand="Honda"))
    service.create("civic", VehicleFilter(brand="Toyota"))
    assert len(service.list_all()) == 1
    assert service.get("civic").filters["brand"] == "Toyota"


def test_filter_of_reconstroi_filtro(session) -> None:
    service = SearchService(session)
    search = service.create("c", VehicleFilter(brand="Honda", year_min=2018))
    filtro = service.filter_of(search)
    assert filtro == VehicleFilter(brand="Honda", year_min=2018)


def test_list_active_ignora_desativadas(session) -> None:
    service = SearchService(session)
    service.create("a", VehicleFilter())
    service.create("b", VehicleFilter())
    service.deactivate("b")
    ativos = {s.name for s in service.list_active()}
    assert ativos == {"a"}


def test_mark_run_incrementa_contador(session) -> None:
    service = SearchService(session)
    search = service.create("a", VehicleFilter())
    assert search.run_count == 0
    service.mark_run(search)
    assert search.run_count == 1
    assert search.last_run_at is not None


def test_deactivate_busca_inexistente() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    with pytest.raises(VehicleMonitorError):
        SearchService(session).deactivate("nao-existe")
