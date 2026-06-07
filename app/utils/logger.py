"""Configuração de logging baseada em Loguru.

Fornece logs coloridos no console (via Rich/Loguru) e logs persistentes
em ``logs/app.log`` com rotação automática, conforme exigido pela
especificação do projeto.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings

_CONFIGURED = False

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logging(
    *,
    level: str | None = None,
    log_file: Path | None = None,
) -> None:
    """Configura os sinks de logging do Loguru (idempotente).

    Args:
        level: nível mínimo de log. Se ``None``, usa ``settings.log_level``.
        log_file: caminho do arquivo de log. Se ``None``, usa
            ``logs/app.log``.
    """
    global _CONFIGURED

    resolved_level = (level or settings.log_level).upper()
    resolved_file = log_file or (settings.logs_dir / "app.log")
    resolved_file.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()

    # Console
    logger.add(
        sys.stderr,
        level=resolved_level,
        format=_CONSOLE_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    # Arquivo persistente com rotação e retenção
    logger.add(
        str(resolved_file),
        level=resolved_level,
        format=_FILE_FORMAT,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> "Any":
    """Retorna um logger Loguru vinculado a ``name``.

    Garante que o logging esteja configurado antes do primeiro uso.

    Args:
        name: nome lógico do componente (ex.: ``"WebmotorsProvider"``).

    Returns:
        Logger Loguru contextualizado.
    """
    if not _CONFIGURED:
        setup_logging()
    if name:
        return logger.bind(name=name)
    return logger
