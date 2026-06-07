"""Gerenciador de navegador Playwright (API síncrona).

Centraliza a criação do navegador/contexto, rotação de *User-Agent*,
esperas inteligentes, *scroll* infinito e *retry* automático, de modo
que os providers concretos não precisem repetir essa lógica.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from app.config import settings
from app.exceptions import ProviderError, ProviderTimeoutError
from app.utils.logger import get_logger

logger = get_logger("browser")

T = TypeVar("T")

# Conjunto de User-Agents realistas para rotação.
_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
)


class BrowserManager:
    """Encapsula um navegador Playwright e fornece páginas configuradas.

    Deve ser usado como *context manager* para garantir o fechamento
    correto dos recursos::

        with BrowserManager() as browser:
            with browser.new_page() as page:
                page.goto(url)
    """

    def __init__(
        self,
        *,
        headless: bool | None = None,
        navigation_timeout: int | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._headless = settings.headless if headless is None else headless
        self._navigation_timeout = (
            settings.navigation_timeout
            if navigation_timeout is None
            else navigation_timeout
        )
        self._forced_user_agent = user_agent

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def __enter__(self) -> "BrowserManager":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    def start(self) -> None:
        """Inicializa o Playwright, o navegador e o contexto."""
        user_agent = self._forced_user_agent or random.choice(_USER_AGENTS)
        logger.debug(
            f"Iniciando navegador (headless={self._headless}) "
            f"UA={user_agent[:32]}..."
        )
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            self._context = self._browser.new_context(
                user_agent=user_agent,
                locale="pt-BR",
                viewport={"width": 1366, "height": 900},
                ignore_https_errors=True,
            )
            self._context.set_default_navigation_timeout(self._navigation_timeout)
            self._context.set_default_timeout(self._navigation_timeout)
        except Exception as exc:  # pragma: no cover - falha de infra
            self.stop()
            raise ProviderError(f"Falha ao iniciar o navegador: {exc}") from exc

    def stop(self) -> None:
        """Fecha contexto, navegador e Playwright (idempotente)."""
        for closer, label in (
            (getattr(self._context, "close", None), "contexto"),
            (getattr(self._browser, "close", None), "navegador"),
            (getattr(self._playwright, "stop", None), "playwright"),
        ):
            if closer is not None:
                try:
                    closer()
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Erro ao fechar {label}: {exc}")
        self._context = None
        self._browser = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Páginas
    # ------------------------------------------------------------------
    @contextmanager
    def new_page(self) -> Iterator[Page]:
        """Cria uma página dentro do contexto atual e a fecha ao final."""
        if self._context is None:
            raise ProviderError("BrowserManager não foi iniciado (use start()).")
        page = self._context.new_page()
        try:
            yield page
        finally:
            try:
                page.close()
            except Exception:  # pragma: no cover
                pass

    def goto(self, page: Page, url: str, *, wait_until: str = "domcontentloaded") -> None:
        """Navega até ``url`` tratando *timeout* de forma tipada.

        Raises:
            ProviderTimeoutError: se a navegação exceder o tempo limite.
            ProviderError: para outras falhas de navegação.
        """
        try:
            page.goto(url, wait_until=wait_until)
        except PlaywrightTimeoutError as exc:
            raise ProviderTimeoutError(
                f"Timeout ao navegar para {url}: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderError(f"Falha ao navegar para {url}: {exc}") from exc

    # ------------------------------------------------------------------
    # Esperas / interações resilientes
    # ------------------------------------------------------------------
    @staticmethod
    def wait_for_selector(
        page: Page, selector: str, *, timeout: int = 10_000
    ) -> bool:
        """Espera por um seletor, retornando ``False`` em caso de *timeout*."""
        try:
            page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            logger.debug(f"Seletor não encontrado a tempo: {selector!r}")
            return False

    @staticmethod
    def human_pause(min_seconds: float = 0.6, max_seconds: float = 1.8) -> None:
        """Pausa aleatória para simular comportamento humano."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def auto_scroll(
        self,
        page: Page,
        *,
        max_scrolls: int = 30,
        pause: float = 1.0,
        item_selector: str | None = None,
        target_count: int | None = None,
    ) -> int:
        """Realiza *scroll* infinito até esgotar a página ou atingir a meta.

        Args:
            page: página ativa.
            max_scrolls: número máximo de iterações de *scroll*.
            pause: tempo de espera entre *scrolls* (s).
            item_selector: se informado, conta os itens carregados.
            target_count: para o *scroll* ao atingir esta quantidade de itens.

        Returns:
            Quantidade de itens detectados (0 se ``item_selector`` for ``None``).
        """
        previous_height = 0
        item_count = 0
        for index in range(max_scrolls):
            page.mouse.wheel(0, 12_000)
            time.sleep(pause)

            if item_selector is not None:
                item_count = len(page.query_selector_all(item_selector))
                if target_count is not None and item_count >= target_count:
                    logger.debug(
                        f"Scroll atingiu a meta de {target_count} itens "
                        f"(iteração {index + 1})."
                    )
                    break

            current_height = page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                logger.debug(
                    f"Fim do conteúdo após {index + 1} scrolls "
                    f"(altura estável)."
                )
                break
            previous_height = current_height

        return item_count


def with_retry(
    func: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 2.0,
    label: str = "operação",
) -> T:
    """Executa ``func`` com *retry* e *backoff* exponencial + *jitter*.

    Args:
        func: função sem argumentos a ser executada.
        attempts: número máximo de tentativas.
        base_delay: atraso base entre tentativas (s).
        label: rótulo descritivo para os logs.

    Returns:
        O valor retornado por ``func``.

    Raises:
        ProviderError: se todas as tentativas falharem.
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except (ProviderTimeoutError, ProviderError) as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning(
                f"{label}: tentativa {attempt}/{attempts} falhou "
                f"({exc}). Retentando em {delay:.1f}s."
            )
            time.sleep(delay)
    raise ProviderError(
        f"{label}: todas as {attempts} tentativas falharam."
    ) from last_exc
