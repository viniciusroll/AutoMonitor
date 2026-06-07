"""Testes das funções puras do FacebookProvider (sem navegador)."""

from __future__ import annotations

import pytest

from app.filters.vehicle_filter import VehicleFilter
from app.providers.facebook import (
    FacebookProvider,
    _brand_model,
    _first_location,
    _first_mileage,
    _first_price,
    _normalize_mileage,
    _pick_title,
)
from app.providers.registry import default_sources, get_provider


def test_facebook_e_o_provider_padrao() -> None:
    assert default_sources() == ["facebook"]
    assert isinstance(get_provider("facebook"), FacebookProvider)


def test_build_search_url_usa_endpoint_de_busca_com_query() -> None:
    provider = FacebookProvider()
    urls = provider.build_search_urls(
        VehicleFilter(
            brand="Honda",
            model="Civic",
            year_min=2018,
            price_max=95_000,
            mileage_max=80_000,
        )
    )
    assert len(urls) == 1
    url = urls[0]
    assert "/marketplace/search" in url
    assert "query=Honda+Civic" in url
    assert "minYear=2018" in url
    assert "maxPrice=95000" in url
    assert "maxMileage=80000" in url


def test_build_search_url_sem_query_usa_categoria_veiculos() -> None:
    urls = FacebookProvider().build_search_urls(VehicleFilter())
    assert "/marketplace/category/vehicles" in urls[0]


def test_item_selector_e_link_de_item() -> None:
    assert "/marketplace/item/" in FacebookProvider().get_item_selector()


@pytest.mark.parametrize(
    ("lines", "esperado"),
    [
        (["R$ 85.000", "Honda Civic"], 85_000.0),
        (["Honda Civic", "R$ 1.299,90"], 1_299.90),
        (["Honda Civic"], None),
    ],
)
def test_first_price(lines, esperado) -> None:
    assert _first_price(lines) == esperado


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [("80K km", 80_000), ("45.000 km", 45_000), ("Honda Civic", None)],
)
def test_normalize_mileage(linha, esperado) -> None:
    assert _normalize_mileage(linha) == esperado


def test_first_mileage_em_lista() -> None:
    assert _first_mileage(["R$ 85.000", "Civic", "80K km"]) == 80_000
    assert _first_mileage(["R$ 85.000", "Civic"]) is None


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ("São Paulo, SP", ("São Paulo", "SP")),
        ("Campinas - SP", ("Campinas", "SP")),
    ],
)
def test_first_location(linha, esperado) -> None:
    assert _first_location([linha]) == esperado


def test_first_location_ausente() -> None:
    assert _first_location(["Honda Civic", "R$ 85.000"]) == (None, None)


def test_pick_title_descarta_preco_e_local() -> None:
    lines = ["R$ 85.000", "Honda Civic EXL 2019", "São Paulo, SP", "45.000 km"]
    assert _pick_title(lines, price=85_000) == "Honda Civic EXL 2019"


def test_brand_model() -> None:
    assert _brand_model("Honda Civic EXL") == ("Honda", "Civic")
    assert _brand_model("Fusca") == ("Fusca", None)
