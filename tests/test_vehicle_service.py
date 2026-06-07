"""Testes do serviço de persistência de veículos."""

from __future__ import annotations

from app.models.price_history import PriceHistory
from app.services.vehicle_service import VehicleService


def test_insere_novo_veiculo(session, scraped_factory) -> None:
    service = VehicleService(session)
    report = service.save_many([scraped_factory()])
    assert len(report.new_vehicles) == 1
    assert report.total == 1
    assert report.new_vehicles[0].id is not None


def test_evita_duplicacao_por_source_external_id(session, scraped_factory) -> None:
    service = VehicleService(session)
    service.save_many([scraped_factory(external_id="999")])
    report = service.save_many([scraped_factory(external_id="999")])
    assert len(report.new_vehicles) == 0
    assert len(report.updated_vehicles) == 1
    assert len(service.list_vehicles()) == 1


def test_detecta_reducao_de_preco(session, scraped_factory) -> None:
    service = VehicleService(session)
    service.save_many([scraped_factory(price=95_000)])
    report = service.save_many([scraped_factory(price=89_000)])
    assert len(report.price_drops) == 1
    drop = report.price_drops[0]
    assert drop.old_price == 95_000
    assert drop.new_price == 89_000
    assert round(drop.percent, 1) == 6.3


def test_aumento_de_preco_nao_e_queda(session, scraped_factory) -> None:
    service = VehicleService(session)
    service.save_many([scraped_factory(price=90_000)])
    report = service.save_many([scraped_factory(price=92_000)])
    assert report.price_drops == []


def test_registra_historico_de_precos(session, scraped_factory) -> None:
    service = VehicleService(session)
    service.save_many([scraped_factory(price=95_000)])
    service.save_many([scraped_factory(price=89_000)])
    historico = session.query(PriceHistory).all()
    assert [h.price for h in historico] == [95_000, 89_000]


def test_lista_por_fonte(session, scraped_factory) -> None:
    service = VehicleService(session)
    service.save_many([scraped_factory(external_id="1", source="webmotors")])
    assert len(service.list_vehicles(source="webmotors")) == 1
    assert len(service.list_vehicles(source="olx")) == 0
