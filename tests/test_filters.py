"""Testes do filtro configurável de veículos."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.filters.vehicle_filter import VehicleFilter
from app.models.enums import FuelType, TransmissionType


def test_filtro_vazio_aceita_qualquer_veiculo(scraped_factory) -> None:
    vehicle = scraped_factory()
    assert VehicleFilter().matches(vehicle) is True


def test_filtro_marca_substring_case_insensitive(scraped_factory) -> None:
    vehicle = scraped_factory(brand="Honda")
    assert VehicleFilter(brand="hon").matches(vehicle) is True
    assert VehicleFilter(brand="Toyota").matches(vehicle) is False


@pytest.mark.parametrize(
    ("year", "esperado"),
    [(2017, False), (2018, True), (2020, True), (2021, False)],
)
def test_filtro_faixa_de_ano(scraped_factory, year: int, esperado: bool) -> None:
    vehicle = scraped_factory(year=year)
    filtro = VehicleFilter(year_min=2018, year_max=2020)
    assert filtro.matches(vehicle) is esperado


def test_filtro_preco_maximo_rejeita_acima(scraped_factory) -> None:
    assert VehicleFilter(price_max=90_000).matches(scraped_factory(price=95_000)) is False
    assert VehicleFilter(price_max=95_000).matches(scraped_factory(price=95_000)) is True


def test_filtro_km_maxima(scraped_factory) -> None:
    assert VehicleFilter(mileage_max=40_000).matches(scraped_factory(mileage=45_000)) is False
    assert VehicleFilter(mileage_max=50_000).matches(scraped_factory(mileage=45_000)) is True


def test_criterio_exige_valor_presente(scraped_factory) -> None:
    # Preço desconhecido não passa quando há price_max definido.
    vehicle = scraped_factory(price=None)
    assert VehicleFilter(price_max=100_000).matches(vehicle) is False


def test_filtro_estado_igualdade_exata(scraped_factory) -> None:
    vehicle = scraped_factory(state="SP")
    assert VehicleFilter(state="sp").matches(vehicle) is True
    assert VehicleFilter(state="RJ").matches(vehicle) is False


def test_filtro_enums(scraped_factory) -> None:
    vehicle = scraped_factory(fuel=FuelType.FLEX, transmission=TransmissionType.AUTOMATICO)
    assert VehicleFilter(fuel=FuelType.FLEX).matches(vehicle) is True
    assert VehicleFilter(fuel=FuelType.DIESEL).matches(vehicle) is False
    assert VehicleFilter(transmission=TransmissionType.AUTOMATICO).matches(vehicle) is True


def test_validacao_de_faixas_incoerentes() -> None:
    with pytest.raises(ValidationError):
        VehicleFilter(year_min=2020, year_max=2010)
    with pytest.raises(ValidationError):
        VehicleFilter(price_min=100, price_max=50)


def test_serializacao_round_trip() -> None:
    original = VehicleFilter(brand="Honda", year_min=2018, price_max=95_000)
    data = original.to_dict()
    assert data == {"brand": "Honda", "year_min": 2018, "price_max": 95_000.0}
    restored = VehicleFilter.from_dict(data)
    assert restored == original


def test_describe_sem_filtros() -> None:
    assert VehicleFilter().describe() == "sem filtros"
