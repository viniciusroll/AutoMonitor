"""Exportador para CSV."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from app.exceptions import ExportError
from app.exporters.base import EXPORT_COLUMNS, BaseExporter


class CSVExporter(BaseExporter):
    """Gera um arquivo CSV (UTF-8 com BOM para compatibilidade com Excel)."""

    extension = "csv"

    def _write(self, rows: Sequence[dict[str, object]], path: Path) -> None:
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(EXPORT_COLUMNS))
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            raise ExportError(f"Falha ao escrever CSV em {path}: {exc}") from exc
