"""Registro central de providers disponíveis.

Permite resolver providers por nome (``source``) e adicionar novos sites
sem alterar o restante do sistema — basta registrá-los aqui.
"""

from __future__ import annotations

from app.exceptions import ProviderError
from app.providers.base import BaseVehicleProvider
from app.providers.webmotors import WebmotorsProvider

# Mapeia o identificador ``source`` para a classe do provider.
_REGISTRY: dict[str, type[BaseVehicleProvider]] = {
    WebmotorsProvider.source: WebmotorsProvider,
}


def register_provider(provider_cls: type[BaseVehicleProvider]) -> None:
    """Registra (ou substitui) um provider pelo seu ``source``."""
    _REGISTRY[provider_cls.source] = provider_cls


def available_providers() -> list[str]:
    """Retorna os identificadores de todos os providers registrados."""
    return sorted(_REGISTRY)


def get_provider(source: str) -> BaseVehicleProvider:
    """Instancia um provider pelo seu ``source``.

    Raises:
        ProviderError: se o ``source`` não estiver registrado.
    """
    try:
        provider_cls = _REGISTRY[source]
    except KeyError as exc:
        raise ProviderError(
            f"Provider desconhecido: {source!r}. "
            f"Disponíveis: {', '.join(available_providers())}."
        ) from exc
    return provider_cls()


def get_providers(sources: list[str] | None = None) -> list[BaseVehicleProvider]:
    """Instancia vários providers; ``None`` retorna todos os registrados."""
    selected = sources if sources is not None else available_providers()
    return [get_provider(source) for source in selected]
