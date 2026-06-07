"""Funções auxiliares compartilhadas pelos comandos da CLI.

Concentram a construção de :class:`VehicleFilter` a partir de opções da
linha de comando e a renderização de tabelas Rich.
"""

from __future__ import annotations

from collections.abc import Sequence

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from app.filters.vehicle_filter import VehicleFilter
from app.models.enums import FuelType, TransmissionType
from app.models.vehicle import Vehicle
from app.services.stats_service import Stats

console = Console()


def build_filter(
    *,
    brand: str | None = None,
    model: str | None = None,
    version: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    mileage_max: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    city: str | None = None,
    state: str | None = None,
    distance_max: float | None = None,
    fuel: str | None = None,
    transmission: str | None = None,
    color: str | None = None,
) -> VehicleFilter:
    """Constrói um :class:`VehicleFilter` a partir das opções da CLI."""
    return VehicleFilter(
        brand=brand,
        model=model,
        version=version,
        year_min=year_min,
        year_max=year_max,
        mileage_max=mileage_max,
        price_min=price_min,
        price_max=price_max,
        city=city,
        state=state,
        distance_max=distance_max,
        fuel=FuelType(fuel) if fuel else None,
        transmission=TransmissionType(transmission) if transmission else None,
        color=color,
    )


def _fmt_price(price: float | None) -> str:
    if price is None:
        return "—"
    return f"R$ {price:,.0f}".replace(",", ".")


def render_vehicles(vehicles: Sequence[Vehicle], *, title: str = "Veículos") -> None:
    """Renderiza uma tabela Rich com os veículos."""
    table = Table(title=title, show_lines=False, header_style="bold cyan")
    for column in ("ID", "Título", "Ano", "Km", "Preço", "Local", "Fonte"):
        table.add_column(column, overflow="fold")

    for vehicle in vehicles:
        local = " - ".join(p for p in (vehicle.city, vehicle.state) if p) or "—"
        table.add_row(
            str(vehicle.id),
            _title_cell(vehicle),
            str(vehicle.year or "—"),
            f"{vehicle.mileage:,}".replace(",", ".") if vehicle.mileage else "—",
            _fmt_price(vehicle.price),
            local,
            vehicle.source,
        )
    console.print(table)
    console.print(
        "[dim]Dica: clique no título (Ctrl/Cmd+clique) para abrir, ou use "
        "[bold]python main.py open <ID>[/bold].[/dim]"
    )


def _title_cell(vehicle: Vehicle) -> str:
    """Renderiza o título como hyperlink clicável (OSC 8), quando há URL."""
    title = escape(vehicle.title or "—")
    if vehicle.url:
        return f"[link={vehicle.url}]{title}[/link]"
    return title


def render_stats(stats: Stats) -> None:
    """Renderiza o resumo estatístico em uma tabela Rich."""
    table = Table(title="Estatísticas", header_style="bold magenta")
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", justify="right")

    table.add_row("Veículos (total)", str(stats.total_vehicles))
    table.add_row("Veículos (ativos)", str(stats.active_vehicles))
    table.add_row("Buscas salvas (total)", str(stats.total_searches))
    table.add_row("Buscas ativas", str(stats.active_searches))
    table.add_row("Notificações enviadas", str(stats.total_notifications))
    table.add_row("Registros de preço", str(stats.total_price_records))
    table.add_row("Preço médio", _fmt_price(stats.avg_price))
    table.add_row("Preço mínimo", _fmt_price(stats.min_price))
    table.add_row("Preço máximo", _fmt_price(stats.max_price))
    console.print(table)

    if stats.by_source:
        source_table = Table(title="Por fonte", header_style="bold green")
        source_table.add_column("Fonte")
        source_table.add_column("Quantidade", justify="right")
        for source, count in sorted(stats.by_source.items()):
            source_table.add_row(source, str(count))
        console.print(source_table)
