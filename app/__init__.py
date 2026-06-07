"""Vehicle Monitor — sistema de monitoramento de anúncios de veículos.

Pacote principal da aplicação. Expõe metadados de versão e mantém o
restante da implementação organizada em subpacotes seguindo os
princípios de Clean Architecture:

- ``app.config``        -> configuração centralizada (.env via Pydantic)
- ``app.models``        -> entidades de domínio + ORM (SQLAlchemy)
- ``app.database``      -> infraestrutura de persistência
- ``app.filters``       -> regras de filtragem de veículos
- ``app.providers``     -> fontes de dados (marketplaces)
- ``app.notifications`` -> canais de alerta (Telegram, Discord, Email)
- ``app.exporters``     -> exportação (CSV, Excel, JSON)
- ``app.services``      -> casos de uso / orquestração
- ``app.cli``           -> interface de linha de comando (Typer)
- ``app.utils``         -> utilitários transversais (logger, etc.)
"""

from __future__ import annotations

__version__ = "0.1.0"
__app_name__ = "vehicle_monitor"

__all__ = ["__version__", "__app_name__"]
