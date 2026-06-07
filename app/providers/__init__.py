"""Fontes de dados (marketplaces) baseadas em providers.

Todo provider concreto herda de :class:`BaseVehicleProvider`, permitindo
adicionar novos sites sem alterar as demais camadas do sistema.
"""

from __future__ import annotations

from app.providers.base import BaseVehicleProvider
from app.providers.browser import BrowserManager, with_retry
from app.providers.facebook import FacebookProvider
from app.providers.registry import (
    available_providers,
    default_sources,
    get_provider,
    get_providers,
    register_provider,
)
from app.providers.webmotors import WebmotorsProvider

__all__ = [
    "BaseVehicleProvider",
    "BrowserManager",
    "with_retry",
    "FacebookProvider",
    "WebmotorsProvider",
    "available_providers",
    "default_sources",
    "get_provider",
    "get_providers",
    "register_provider",
]
