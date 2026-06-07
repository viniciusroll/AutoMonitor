"""Exportação de resultados (CSV, Excel, JSON)."""

from __future__ import annotations

from app.exceptions import ExportError
from app.exporters.base import BaseExporter
from app.exporters.csv_exporter import CSVExporter
from app.exporters.excel_exporter import ExcelExporter
from app.exporters.json_exporter import JSONExporter

# Formatos suportados -> classe exportadora.
_EXPORTERS: dict[str, type[BaseExporter]] = {
    "csv": CSVExporter,
    "excel": ExcelExporter,
    "xlsx": ExcelExporter,
    "json": JSONExporter,
}


def available_formats() -> list[str]:
    """Retorna os formatos de exportação suportados."""
    return ["csv", "excel", "json"]


def get_exporter(fmt: str) -> BaseExporter:
    """Instancia o exportador para o formato ``fmt``.

    Raises:
        ExportError: se o formato não for suportado.
    """
    try:
        exporter_cls = _EXPORTERS[fmt.lower()]
    except KeyError as exc:
        raise ExportError(
            f"Formato de exportação inválido: {fmt!r}. "
            f"Use um de: {', '.join(available_formats())}."
        ) from exc
    return exporter_cls()


__all__ = [
    "BaseExporter",
    "CSVExporter",
    "ExcelExporter",
    "JSONExporter",
    "get_exporter",
    "available_formats",
]
