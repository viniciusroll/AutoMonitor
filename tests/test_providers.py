"""Testes da camada de providers (sem acesso à rede)."""

from __future__ import annotations

import pytest

from app.exceptions import ProviderError
from app.filters.vehicle_filter import VehicleFilter
from app.providers.registry import (
    available_providers,
    get_provider,
    get_providers,
    register_provider,
)
from app.providers.webmotors import (
    WebmotorsProvider,
    _brand_model_from_title,
    _external_id_from_url,
    _mileage_from_specs,
    _slug,
    _split_location,
    _year_from_specs,
)


def test_registry_contem_webmotors() -> None:
    assert "webmotors" in available_providers()
    assert isinstance(get_provider("webmotors"), WebmotorsProvider)


def test_get_provider_desconhecido() -> None:
    with pytest.raises(ProviderError):
        get_provider("inexistente")


def test_get_providers_todos() -> None:
    assert len(get_providers()) == len(available_providers())


def test_register_provider_customizado() -> None:
    class DummyProvider(WebmotorsProvider):
        source = "dummy"

    register_provider(DummyProvider)
    assert "dummy" in available_providers()
    assert isinstance(get_provider("dummy"), DummyProvider)


def test_build_search_urls_inclui_filtros() -> None:
    provider = WebmotorsProvider()
    urls = provider.build_search_urls(
        VehicleFilter(brand="Honda", model="Civic", year_min=2018, price_max=95_000)
    )
    assert len(urls) == 1
    url = urls[0]
    assert "honda" in url and "civic" in url
    assert "anoDe=2018" in url
    assert "precoAte=95000" in url


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("São Paulo - SP", ("São Paulo", "SP")),
        ("Campinas", ("Campinas", None)),
        (None, (None, None)),
    ],
)
def test_split_location(entrada, esperado) -> None:
    assert _split_location(entrada) == esperado


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("https://www.webmotors.com.br/carro/123456", "123456"),
        ("https://www.webmotors.com.br/comprar/honda-civic/9876543/", "9876543"),
        ("https://www.webmotors.com.br/anuncio/abc", "abc"),
    ],
)
def test_external_id_from_url(url, esperado) -> None:
    assert _external_id_from_url(url) == esperado


def test_slug() -> None:
    assert _slug("Honda Civic") == "honda-civic"
    assert _slug("  Toyota   Corolla ") == "toyota-corolla"


def test_year_from_specs() -> None:
    assert _year_from_specs(["Flex", "2019/2020", "Automático"]) == 2020
    assert _year_from_specs(["Flex", "Automático"]) is None


def test_mileage_from_specs() -> None:
    assert _mileage_from_specs(["2019", "45.000 km", "Flex"]) == 45_000
    assert _mileage_from_specs(["2019", "Flex"]) is None


def test_brand_model_from_title() -> None:
    assert _brand_model_from_title("Honda Civic EXL", self_filter_hint=None) == (
        "Honda",
        "Civic",
    )
    assert _brand_model_from_title("Fusca", self_filter_hint=None) == ("Fusca", None)
