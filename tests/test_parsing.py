"""Testes dos utilitários de parsing."""

from __future__ import annotations

import pytest

from app.models.enums import FuelType, SellerType, TransmissionType
from app.utils.parsing import (
    clean_text,
    parse_fuel,
    parse_int,
    parse_price,
    parse_seller_type,
    parse_transmission,
    parse_year,
)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("R$ 95.000", 95_000.0),
        ("R$ 1.299,90", 1_299.90),
        ("89000", 89_000.0),
        ("", None),
        (None, None),
        ("R$ 0", None),
    ],
)
def test_parse_price(entrada, esperado) -> None:
    assert parse_price(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("80.000 km", 80_000), ("12 fotos", 12), ("abc", None), (None, None)],
)
def test_parse_int(entrada, esperado) -> None:
    assert parse_int(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("2018/2019", 2019), ("Civic 2020", 2020), ("sem ano", None), (None, None)],
)
def test_parse_year(entrada, esperado) -> None:
    assert parse_year(entrada) == esperado


def test_clean_text() -> None:
    assert clean_text("  Honda   Civic\n ") == "Honda Civic"
    assert clean_text("   ") is None
    assert clean_text(None) is None


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Flex", FuelType.FLEX),
        ("Gasolina", FuelType.GASOLINA),
        ("Elétrico", FuelType.ELETRICO),
        ("qualquer", FuelType.DESCONHECIDO),
    ],
)
def test_parse_fuel(entrada, esperado) -> None:
    assert parse_fuel(entrada) is esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Automático", TransmissionType.AUTOMATICO),
        ("Manual", TransmissionType.MANUAL),
        ("CVT", TransmissionType.CVT),
        ("Automatizado", TransmissionType.AUTOMATIZADO),
        ("?", TransmissionType.DESCONHECIDO),
    ],
)
def test_parse_transmission(entrada, esperado) -> None:
    assert parse_transmission(entrada) is esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Loja oficial", SellerType.LOJA),
        ("Vendedor particular", SellerType.PARTICULAR),
        ("", SellerType.DESCONHECIDO),
    ],
)
def test_parse_seller_type(entrada, esperado) -> None:
    assert parse_seller_type(entrada) is esperado
