"""Interface comum dos exportadores e utilidades compartilhadas."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models.vehicle import Vehicle
from app.utils.logger import get_logger

# Ordem canônica das colunas exportadas.
EXPORT_COLUMNS: tuple[str, ...] = (
    "id",
    "source",
    "external_id",
    "title",
    "brand",
    "model",
    "version",
    "year",
    "mileage",
    "price",
    "fuel",
    "transmission",
    "color",
    "city",
    "state",
    "seller_name",
    "seller_type",
    "photo_count",
    "url",
    "published_at",
    "collected_at",
)


def vehicle_to_row(vehicle: Vehicle) -> dict[str, object]:
    """Converte um :class:`Vehicle` em um dict ordenado para exportação."""
    row: dict[str, object] = {}
    for column in EXPORT_COLUMNS:
        value = getattr(vehicle, column, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        row[column] = value
    return row


def rows_from_vehicles(vehicles: Iterable[Vehicle]) -> list[dict[str, object]]:
    """Converte uma coleção de veículos em linhas exportáveis."""
    return [vehicle_to_row(v) for v in vehicles]


class BaseExporter(ABC):
    """Contrato comum a todos os exportadores."""

    #: Extensão (sem ponto) do formato gerado.
    extension: str = ""

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def _write(self, rows: Sequence[dict[str, object]], path: Path) -> None:
        """Escreve as linhas no ``path`` no formato específico."""

    def export(
        self,
        vehicles: Sequence[Vehicle],
        *,
        path: Path | str | None = None,
        filename: str | None = None,
    ) -> Path:
        """Exporta os veículos para um arquivo e retorna o caminho final.

        Args:
            vehicles: veículos a exportar.
            path: caminho completo de destino (tem prioridade sobre ``filename``).
            filename: nome do arquivo dentro de ``exports/`` (sem extensão).

        Returns:
            O :class:`Path` do arquivo gerado.
        """
        target = self._resolve_path(path=path, filename=filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_from_vehicles(vehicles)
        self._write(rows, target)
        self.logger.info(f"Exportados {len(rows)} veículos para {target}.")
        return target

    def _resolve_path(
        self, *, path: Path | str | None, filename: str | None
    ) -> Path:
        if path is not None:
            return Path(path)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename or f"vehicles_{stamp}"
        return settings.exports_dir / f"{name}.{self.extension}"
