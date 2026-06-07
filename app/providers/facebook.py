"""Provider para o Facebook Marketplace.

Implementação concreta de :class:`BaseVehicleProvider` para a categoria
de veículos do Facebook Marketplace.

O Facebook renderiza os anúncios dinamicamente e costuma exibir um
*modal* de login sobre a grade de resultados. Por isso este provider:

- sobrescreve :meth:`prepare_page` para dispensar o *modal* e liberar a
  rolagem da página;
- identifica cada anúncio pelo link ``/marketplace/item/<id>`` (seletor
  estável, independente das classes ofuscadas do Facebook);
- faz o *parsing* a partir do texto do cartão dividido em linhas
  (preço / título / localização / km), o que é resiliente a mudanças de
  marcação.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

from playwright.sync_api import ElementHandle, Page

from app.config import settings
from app.filters.vehicle_filter import VehicleFilter
from app.models.vehicle import ScrapedVehicle
from app.providers.base import BaseVehicleProvider
from app.utils.parsing import clean_text, parse_int, parse_price, parse_year

# Cada anúncio é um link para /marketplace/item/<id>. Seletor estável.
_ITEM_SELECTOR = 'a[href*="/marketplace/item/"]'
_ITEM_ID_RE = re.compile(r"/marketplace/item/(\d+)")
# "São Paulo, SP" / "Campinas - SP"
_LOCATION_RE = re.compile(r"^(.+?)[,\-]\s*([A-Z]{2})$")


class FacebookProvider(BaseVehicleProvider):
    """Coletor de anúncios de veículos do Facebook Marketplace."""

    source = "facebook"
    display_name = "Facebook Marketplace"
    base_url = "https://www.facebook.com"
    auth_state_path = str(settings.facebook_auth_path)

    # ------------------------------------------------------------------
    # Construção da URL de busca
    # ------------------------------------------------------------------
    def build_search_urls(self, vehicle_filter: VehicleFilter) -> list[str]:
        """Monta a URL de busca de veículos do Marketplace a partir do filtro."""
        query = " ".join(
            part
            for part in (
                vehicle_filter.brand,
                vehicle_filter.model,
                vehicle_filter.version,
            )
            if part
        ).strip()

        params: dict[str, object] = {"sortBy": "creation_time_descend"}
        if query:
            params["query"] = query
        if vehicle_filter.price_min is not None:
            params["minPrice"] = int(vehicle_filter.price_min)
        if vehicle_filter.price_max is not None:
            params["maxPrice"] = int(vehicle_filter.price_max)
        if vehicle_filter.year_min is not None:
            params["minYear"] = vehicle_filter.year_min
        if vehicle_filter.year_max is not None:
            params["maxYear"] = vehicle_filter.year_max
        if vehicle_filter.mileage_max is not None:
            params["maxMileage"] = vehicle_filter.mileage_max

        # Busca na categoria de veículos quando há termo; caso contrário,
        # navega direto na categoria de veículos.
        if query:
            path = "/marketplace/search"
        else:
            path = "/marketplace/category/vehicles"
        return [f"{self.base_url}{path}?{urlencode(params)}"]

    # ------------------------------------------------------------------
    # Seletor / preparação da página
    # ------------------------------------------------------------------
    def get_item_selector(self) -> str:
        return _ITEM_SELECTOR

    def prepare_page(self, page: Page) -> None:
        """Dispensa o modal de login e restaura a rolagem da página.

        Se o Facebook redirecionar para a página de login (sessão ausente
        ou expirada), emite um aviso claro com a instrução de correção.
        """
        if "/login" in page.url:
            self.logger.warning(
                "Facebook exigiu login — sessão ausente ou expirada. "
                "Autentique-se uma vez com: python main.py login"
            )
            return
        # Fecha qualquer diálogo (login/cookies) pressionando Escape.
        try:
            page.keyboard.press("Escape")
        except Exception:  # pragma: no cover - best effort
            pass
        # Clica em um botão de fechar, se existir.
        for selector in ('[aria-label="Fechar"]', '[aria-label="Close"]'):
            node = page.query_selector(selector)
            if node is not None:
                try:
                    node.click(timeout=2_000)
                except Exception:  # pragma: no cover
                    pass
                break
        # Remove a trava de rolagem que o modal aplica no <body>.
        try:
            page.evaluate(
                "() => { document.body.style.overflow = 'auto'; "
                "document.documentElement.style.overflow = 'auto'; }"
            )
        except Exception:  # pragma: no cover
            pass

    # ------------------------------------------------------------------
    # Parsing de um anúncio
    # ------------------------------------------------------------------
    def parse_item(self, element: ElementHandle) -> ScrapedVehicle | None:
        href = element.get_attribute("href") or ""
        match = _ITEM_ID_RE.search(href)
        if match is None:
            return None
        external_id = match.group(1)
        url = f"{self.base_url}{href.split('?')[0]}"

        lines = _text_lines(element)
        if not lines:
            return None

        price = _first_price(lines)
        mileage = _first_mileage(lines)
        city, state = _first_location(lines)
        title = _pick_title(lines, price=price)
        if title is None:
            return None

        brand, model = _brand_model(title)

        return ScrapedVehicle(
            source=self.source,
            external_id=external_id,
            url=url,
            title=title,
            brand=brand,
            model=model,
            year=parse_year(title),
            mileage=mileage,
            price=price,
            city=city,
            state=state,
        )


# ----------------------------------------------------------------------
# Helpers de parsing (puros, testáveis sem navegador)
# ----------------------------------------------------------------------
def _text_lines(element: ElementHandle) -> list[str]:
    """Extrai as linhas de texto não vazias do cartão do anúncio."""
    try:
        raw = element.inner_text()
    except Exception:  # pragma: no cover - elemento volátil
        return []
    lines: list[str] = []
    for line in raw.split("\n"):
        cleaned = clean_text(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def _first_price(lines: list[str]) -> float | None:
    for line in lines:
        if "R$" in line or "$" in line:
            price = parse_price(line)
            if price is not None:
                return price
    return None


def _first_mileage(lines: list[str]) -> int | None:
    # A linha de quilometragem do Facebook sempre contém "km"
    # (ex.: "206 mil km", "80K km", "45.000 km").
    for line in lines:
        if "km" in line.lower():
            mileage = _normalize_mileage(line)
            if mileage is not None:
                return mileage
    return None


# "206 mil km" / "80k km" -> multiplicador de milhar. O ``k`` de "km" é
# excluído pelo lookahead negativo ``(?!m)``.
_THOUSAND_RE = re.compile(r"(\d[\d.,]*)\s*(?:mil|k(?!m))", re.IGNORECASE)


def _normalize_mileage(line: str) -> int | None:
    """Interpreta ``206 mil km`` / ``80K km`` / ``45.000 km`` em km inteiros."""
    match = _THOUSAND_RE.search(line)
    if match:
        base = parse_int(match.group(1))
        if base is not None:
            return base * 1_000
    return parse_int(line)


def _first_location(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = _LOCATION_RE.match(line)
        if match:
            return clean_text(match.group(1)), match.group(2).upper()
    return None, None


def _pick_title(lines: list[str], *, price: float | None) -> str | None:
    """Escolhe a linha que melhor representa o título do anúncio.

    Descarta linhas de preço, quilometragem e localização e retorna a
    linha textual mais longa entre as restantes.
    """
    candidates: list[str] = []
    for line in lines:
        if "R$" in line:
            continue
        if _LOCATION_RE.match(line):
            continue
        if "km" in line.lower():  # linha de quilometragem
            continue
        if re.fullmatch(r"[\d.\s]+", line):  # linha só de números
            continue
        candidates.append(line)
    if not candidates:
        return None
    return max(candidates, key=len)


_YEAR_TOKEN_RE = re.compile(r"^(19|20)\d{2}$")


def _brand_model(title: str) -> tuple[str | None, str | None]:
    """Extrai marca e modelo do título.

    O Facebook costuma prefixar o ano (``2019 Honda Civic EXL``); o ano
    inicial é descartado antes de tomar 1ª palavra = marca e 2ª = modelo.
    """
    tokens = title.split()
    if tokens and _YEAR_TOKEN_RE.match(tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return None, None
    brand = tokens[0]
    model = tokens[1] if len(tokens) > 1 else None
    return brand, model
