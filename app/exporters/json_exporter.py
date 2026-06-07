"""Exportador para JSON."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from app.exceptions import ExportError
from app.exporters.base import BaseExporter


class JSONExporter(BaseExporter):
    """Gera um arquivo JSON formatado (UTF-8, indentado)."""

    extension = "json"

    def _write(self, rows: Sequence[dict[str, object]], path: Path) -> None:
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(list(rows), handle, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as exc:
            raise ExportError(f"Falha ao escrever JSON em {path}: {exc}") from exc
