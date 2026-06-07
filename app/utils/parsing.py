"""Funções utilitárias de *parsing* e normalização de texto.

Reúne conversões recorrentes ao extrair dados de marketplaces
brasileiros (preços em "R$", quilometragem com "km", anos no formato
``2018/2019``, etc.), de forma defensiva: entradas inesperadas retornam
``None`` em vez de lançar exceção.
"""

from __future__ import annotations

import re

from app.models.enums import FuelType, SellerType, TransmissionType

_DIGITS_RE = re.compile(r"\d+")
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def clean_text(value: str | None) -> str | None:
    """Colapsa espaços e remove quebras de linha; ``None`` se vazio."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def parse_price(value: str | None) -> float | None:
    """Extrai um preço em reais de um texto.

    Exemplos: ``"R$ 95.000"`` -> ``95000.0``;
    ``"R$ 1.299,90"`` -> ``1299.90``.
    """
    if not value:
        return None
    text = value.replace("R$", "").strip()
    # Remove separador de milhar e troca vírgula decimal por ponto.
    text = text.replace(".", "").replace(",", ".")
    digits = re.sub(r"[^\d.]", "", text)
    if not digits or digits == ".":
        return None
    try:
        price = float(digits)
    except ValueError:
        return None
    return price if price > 0 else None


def parse_int(value: str | None) -> int | None:
    """Extrai o primeiro inteiro de um texto (ignora separadores).

    Exemplos: ``"80.000 km"`` -> ``80000``; ``"12 fotos"`` -> ``12``.
    """
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def parse_year(value: str | None) -> int | None:
    """Extrai um ano (1900–2099) de um texto, incl. formato ``2018/2019``.

    Em intervalos ``modelo/fabricação`` retorna o **maior** ano (modelo).
    """
    if not value:
        return None
    years = [int(match.group()) for match in _YEAR_RE.finditer(value)]
    valid = [y for y in years if 1900 <= y <= 2099]
    return max(valid) if valid else None


def parse_fuel(value: str | None) -> FuelType:
    """Mapeia um texto livre para :class:`FuelType`."""
    text = (value or "").lower()
    mapping = {
        FuelType.FLEX: ("flex",),
        FuelType.GASOLINA: ("gasolina",),
        FuelType.ETANOL: ("etanol", "álcool", "alcool"),
        FuelType.DIESEL: ("diesel",),
        FuelType.GNV: ("gnv", "gás", "gas natural"),
        FuelType.HIBRIDO: ("híbrido", "hibrido", "hybrid"),
        FuelType.ELETRICO: ("elétrico", "eletrico", "electric", "ev"),
    }
    for fuel, keywords in mapping.items():
        if any(keyword in text for keyword in keywords):
            return fuel
    return FuelType.DESCONHECIDO


def parse_transmission(value: str | None) -> TransmissionType:
    """Mapeia um texto livre para :class:`TransmissionType`."""
    text = (value or "").lower()
    if "cvt" in text:
        return TransmissionType.CVT
    if "automatizad" in text:
        return TransmissionType.AUTOMATIZADO
    if "autom" in text:
        return TransmissionType.AUTOMATICO
    if "manual" in text:
        return TransmissionType.MANUAL
    return TransmissionType.DESCONHECIDO


def parse_seller_type(value: str | None) -> SellerType:
    """Mapeia um texto livre para :class:`SellerType`."""
    text = (value or "").lower()
    if any(k in text for k in ("loja", "concession", "revenda", "store", "dealer")):
        return SellerType.LOJA
    if any(k in text for k in ("particular", "pessoa física", "private")):
        return SellerType.PARTICULAR
    return SellerType.DESCONHECIDO
