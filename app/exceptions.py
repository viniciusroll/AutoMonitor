"""Exceções de domínio da aplicação.

Centraliza a hierarquia de erros para que as camadas superiores possam
tratar falhas de forma granular sem depender de exceções genéricas.
"""

from __future__ import annotations


class VehicleMonitorError(Exception):
    """Exceção base para todos os erros da aplicação."""


class ConfigError(VehicleMonitorError):
    """Erro de configuração (variáveis ausentes/ inválidas)."""


class ProviderError(VehicleMonitorError):
    """Erro genérico ao coletar dados de um provider."""


class ProviderTimeoutError(ProviderError):
    """A página demorou além do tempo limite para responder."""


class ProviderParseError(ProviderError):
    """Falha ao extrair/parsear os dados de um anúncio."""


class NotificationError(VehicleMonitorError):
    """Falha ao enviar uma notificação por algum canal."""


class ExportError(VehicleMonitorError):
    """Falha durante a exportação de dados."""


class DatabaseError(VehicleMonitorError):
    """Falha em operação de persistência."""
