"""Interface comum dos providers de marketplace.

:class:`BaseVehicleProvider` define o contrato (e o *template method*)
que todo provider concreto deve seguir, garantindo que novos sites
possam ser adicionados sem alterar o restante do sistema (princípio
aberto/fechado).

O fluxo padrão de :meth:`BaseVehicleProvider.search` é:

1. construir a(s) URL(s) de busca a partir do :class:`VehicleFilter`;
2. abrir a página com o :class:`BrowserManager` (com *retry*);
3. realizar *scroll*/paginação para carregar os anúncios;
4. extrair os elementos brutos da listagem;
5. converter cada elemento em :class:`ScrapedVehicle` (validado);
6. aplicar o filtro localmente e respeitar ``max_results``.

Subclasses implementam apenas os ganchos abstratos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from playwright.sync_api import ElementHandle, Page

from app.config import settings
from app.exceptions import ProviderError, ProviderParseError
from app.filters.vehicle_filter import VehicleFilter
from app.models.vehicle import ScrapedVehicle
from app.providers.browser import BrowserManager, with_retry
from app.utils.logger import get_logger


class BaseVehicleProvider(ABC):
    """Contrato comum a todos os providers de anúncios de veículos."""

    #: Identificador curto e estável do provider (coluna ``source``).
    source: str = "base"
    #: Nome legível para exibição.
    display_name: str = "Base"
    #: URL base do marketplace.
    base_url: str = ""
    #: Caminho da sessão autenticada (cookies). ``None`` = site público.
    auth_state_path: str | None = None

    def __init__(self, browser: BrowserManager | None = None) -> None:
        self._external_browser = browser is not None
        self._browser = browser
        self.logger = get_logger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Ganchos abstratos (implementados pelas subclasses)
    # ------------------------------------------------------------------
    @abstractmethod
    def build_search_urls(self, vehicle_filter: VehicleFilter) -> list[str]:
        """Constrói a lista de URLs de busca a partir do filtro."""

    @abstractmethod
    def get_item_selector(self) -> str:
        """Seletor CSS que identifica cada anúncio na listagem."""

    @abstractmethod
    def parse_item(self, element: ElementHandle) -> ScrapedVehicle | None:
        """Converte um elemento de listagem em :class:`ScrapedVehicle`.

        Deve retornar ``None`` quando o elemento não puder ser
        interpretado como um anúncio válido (em vez de lançar exceção),
        para que um item problemático não interrompa toda a coleta.
        """

    # ------------------------------------------------------------------
    # Ganchos opcionais (com implementação padrão)
    # ------------------------------------------------------------------
    def prepare_page(self, page: Page) -> None:
        """Gancho executado após a navegação (ex.: fechar *cookie banner*)."""

    def load_all_items(self, page: Page, max_results: int) -> None:
        """Carrega os anúncios da página (padrão: *scroll* infinito)."""
        assert self._browser is not None  # garantido por search()
        self._browser.auto_scroll(
            page,
            item_selector=self.get_item_selector(),
            target_count=max_results,
        )

    # ------------------------------------------------------------------
    # Template method
    # ------------------------------------------------------------------
    def search(
        self,
        vehicle_filter: VehicleFilter,
        *,
        max_results: int | None = None,
    ) -> list[ScrapedVehicle]:
        """Executa a busca completa e retorna anúncios filtrados.

        Args:
            vehicle_filter: critérios de busca/filtragem.
            max_results: limite de anúncios retornados. Se ``None``,
                usa ``settings.max_results``.

        Returns:
            Lista de :class:`ScrapedVehicle` que satisfazem o filtro.

        Raises:
            ProviderError: em caso de falha irrecuperável de coleta.
        """
        limit = max_results or settings.max_results
        self.logger.info(
            f"[{self.source}] Iniciando busca (limite={limit}) — "
            f"filtros: {vehicle_filter.describe()}"
        )

        if self._browser is not None:
            return self._search_with_browser(self._browser, vehicle_filter, limit)

        with BrowserManager(storage_state=self.auth_state_path) as browser:
            self._browser = browser
            try:
                return self._search_with_browser(browser, vehicle_filter, limit)
            finally:
                self._browser = None

    # ------------------------------------------------------------------
    # Implementação interna
    # ------------------------------------------------------------------
    def _search_with_browser(
        self,
        browser: BrowserManager,
        vehicle_filter: VehicleFilter,
        limit: int,
    ) -> list[ScrapedVehicle]:
        urls = self.build_search_urls(vehicle_filter)
        collected: dict[str, ScrapedVehicle] = {}

        for url in urls:
            if len(collected) >= limit:
                break
            try:
                items = with_retry(
                    lambda u=url: self._scrape_url(browser, u, limit),
                    label=f"{self.source} GET {url}",
                )
            except ProviderError as exc:
                self.logger.error(f"[{self.source}] Falha em {url}: {exc}")
                continue

            for vehicle in items:
                collected.setdefault(vehicle.external_id, vehicle)
                if len(collected) >= limit:
                    break

        result = [v for v in collected.values() if vehicle_filter.matches(v)]
        self.logger.info(
            f"[{self.source}] Coletados {len(collected)} anúncios, "
            f"{len(result)} após filtragem."
        )
        return result[:limit]

    def _scrape_url(
        self, browser: BrowserManager, url: str, limit: int
    ) -> list[ScrapedVehicle]:
        with browser.new_page() as page:
            browser.goto(page, url)
            self.prepare_page(page)

            selector = self.get_item_selector()
            if not browser.wait_for_selector(page, selector, timeout=15_000):
                self.logger.warning(
                    f"[{self.source}] Nenhum anúncio encontrado em {url}."
                )
                return []

            self.load_all_items(page, limit)
            elements = page.query_selector_all(selector)
            self.logger.debug(
                f"[{self.source}] {len(elements)} elementos brutos em {url}."
            )
            return list(self._parse_elements(elements))

    def _parse_elements(
        self, elements: Iterable[ElementHandle]
    ) -> Iterable[ScrapedVehicle]:
        for element in elements:
            try:
                vehicle = self.parse_item(element)
            except ProviderParseError as exc:
                self.logger.debug(f"[{self.source}] Item ignorado: {exc}")
                continue
            except Exception as exc:  # parsing nunca deve derrubar a coleta
                self.logger.warning(
                    f"[{self.source}] Erro inesperado ao parsear item: {exc}"
                )
                continue
            if vehicle is not None:
                yield vehicle

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} source={self.source!r}>"
