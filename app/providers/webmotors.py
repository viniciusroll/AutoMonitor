"""Provider para a Webmotors.

Implementação concreta de :class:`BaseVehicleProvider`. Os seletores
são declarados em uma tabela de constantes com **alternativas
resilientes**: se o site alterar uma classe, basta acrescentar um novo
seletor à lista correspondente, sem tocar na lógica de coleta.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from playwright.sync_api import ElementHandle

from app.filters.vehicle_filter import VehicleFilter
from app.models.vehicle import ScrapedVehicle
from app.providers.base import BaseVehicleProvider
from app.utils.parsing import (
    clean_text,
    parse_int,
    parse_price,
    parse_seller_type,
    parse_year,
)

# Listas de seletores em ordem de preferência. O primeiro que casar vence.
_SELECTORS: dict[str, tuple[str, ...]] = {
    "card": (
        '[data-testid="card"]',
        "article",
        '[class*="card"]',
    ),
    "title": (
        '[data-testid*="title"]',
        "h2",
        "h3",
    ),
    "price": (
        '[data-testid*="price"]',
        '[class*="price"]',
    ),
    "link": ("a[href]",),
    "specs": (
        '[data-testid*="specification"]',
        '[class*="specification"]',
        "ul li",
    ),
    "location": (
        '[data-testid*="location"]',
        '[class*="location"]',
    ),
    "seller": (
        '[data-testid*="seller"]',
        '[class*="seller"]',
    ),
    "image": ("img",),
}


class WebmotorsProvider(BaseVehicleProvider):
    """Coletor de anúncios da Webmotors."""

    source = "webmotors"
    display_name = "Webmotors"
    base_url = "https://www.webmotors.com.br"

    # ------------------------------------------------------------------
    # Construção da URL de busca
    # ------------------------------------------------------------------
    def build_search_urls(self, vehicle_filter: VehicleFilter) -> list[str]:
        """Monta a URL de busca da Webmotors a partir do filtro."""
        path_parts = ["carros", "estoque"]
        if vehicle_filter.brand:
            path_parts.append(_slug(vehicle_filter.brand))
            if vehicle_filter.model:
                path_parts.append(_slug(vehicle_filter.model))

        params: list[str] = []
        if vehicle_filter.year_min:
            params.append(f"anoDe={vehicle_filter.year_min}")
        if vehicle_filter.year_max:
            params.append(f"anoAte={vehicle_filter.year_max}")
        if vehicle_filter.price_min:
            params.append(f"precoDe={int(vehicle_filter.price_min)}")
        if vehicle_filter.price_max:
            params.append(f"precoAte={int(vehicle_filter.price_max)}")
        if vehicle_filter.mileage_max:
            params.append(f"kmAte={vehicle_filter.mileage_max}")
        if vehicle_filter.state:
            params.append(f"estado={quote_plus(vehicle_filter.state)}")
        if vehicle_filter.city:
            params.append(f"cidade={quote_plus(vehicle_filter.city)}")

        url = f"{self.base_url}/{'/'.join(path_parts)}"
        if params:
            url = f"{url}?{'&'.join(params)}"
        return [url]

    # ------------------------------------------------------------------
    # Seletores
    # ------------------------------------------------------------------
    def get_item_selector(self) -> str:
        return ", ".join(_SELECTORS["card"])

    # ------------------------------------------------------------------
    # Parsing de um anúncio
    # ------------------------------------------------------------------
    def parse_item(self, element: ElementHandle) -> ScrapedVehicle | None:
        title = _first_text(element, _SELECTORS["title"])
        href = _first_attr(element, _SELECTORS["link"], "href")
        if not title or not href:
            return None

        url = href if href.startswith("http") else f"{self.base_url}{href}"
        external_id = _external_id_from_url(url)
        if external_id is None:
            return None

        price = parse_price(_first_text(element, _SELECTORS["price"]))
        specs = _all_texts(element, _SELECTORS["specs"])
        year = _year_from_specs(specs) or parse_year(title)
        mileage = _mileage_from_specs(specs)

        city, state = _split_location(_first_text(element, _SELECTORS["location"]))
        brand, model = _brand_model_from_title(title, self_filter_hint=None)

        photo_count = len(element.query_selector_all(_SELECTORS["image"][0]))
        seller_type = parse_seller_type(_first_text(element, _SELECTORS["seller"]))

        return ScrapedVehicle(
            source=self.source,
            external_id=external_id,
            url=url,
            title=title,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            price=price,
            city=city,
            state=state,
            seller_type=seller_type,
            photo_count=photo_count,
        )


# ----------------------------------------------------------------------
# Helpers de extração (resilientes: tentam várias alternativas)
# ----------------------------------------------------------------------
def _slug(value: str) -> str:
    """Converte texto em *slug* simples para a URL (``Honda Civic`` -> ``honda-civic``)."""
    return "-".join(value.strip().lower().split())


def _first_text(element: ElementHandle, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        node = element.query_selector(selector)
        if node is not None:
            text = clean_text(node.inner_text())
            if text:
                return text
    return None


def _first_attr(
    element: ElementHandle, selectors: tuple[str, ...], attr: str
) -> str | None:
    for selector in selectors:
        node = element.query_selector(selector)
        if node is not None:
            value = node.get_attribute(attr)
            if value:
                return value
    return None


def _all_texts(element: ElementHandle, selectors: tuple[str, ...]) -> list[str]:
    texts: list[str] = []
    for selector in selectors:
        for node in element.query_selector_all(selector):
            text = clean_text(node.inner_text())
            if text:
                texts.append(text)
        if texts:
            break
    return texts


def _external_id_from_url(url: str) -> str | None:
    """Extrai um identificador estável do anúncio a partir da URL."""
    import re

    match = re.search(r"/(\d{6,})(?:[/?#]|$)", url)
    if match:
        return match.group(1)
    # fallback: caminho final sem query string
    tail = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or None


def _year_from_specs(specs: list[str]) -> int | None:
    for spec in specs:
        year = parse_year(spec)
        if year is not None:
            return year
    return None


def _mileage_from_specs(specs: list[str]) -> int | None:
    for spec in specs:
        if "km" in spec.lower():
            mileage = parse_int(spec)
            if mileage is not None:
                return mileage
    return None


def _split_location(value: str | None) -> tuple[str | None, str | None]:
    """Separa ``"São Paulo - SP"`` em ``("São Paulo", "SP")``."""
    if not value:
        return None, None
    if "-" in value:
        city, _, state = value.rpartition("-")
        city = clean_text(city)
        state = clean_text(state)
        if state and len(state) == 2:
            return city, state.upper()
        return clean_text(value), None
    return value, None


def _brand_model_from_title(
    title: str, *, self_filter_hint: str | None
) -> tuple[str | None, str | None]:
    """Heurística simples: primeira palavra = marca, segunda = modelo."""
    parts = title.split()
    if not parts:
        return None, None
    brand = parts[0]
    model = parts[1] if len(parts) > 1 else None
    return brand, model
