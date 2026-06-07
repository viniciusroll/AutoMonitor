"""Aplicação de linha de comando (Typer).

Expõe os comandos ``search``, ``monitor``, ``export``, ``stats`` e
utilitários de banco (``db-init``). Cada comando abre uma sessão
transacional via :func:`app.database.session_scope`.
"""

from __future__ import annotations

import time
from typing import Annotated

import schedule
import typer

from app.config import settings
from app.database import init_db, session_scope
from app.exporters import available_formats, get_exporter
from app.cli.helpers import (
    build_filter,
    console,
    render_stats,
    render_vehicles,
)
from app.models.vehicle import Vehicle
from app.providers.registry import available_providers, default_sources
from app.services.monitor_service import MonitorService
from app.services.search_service import SearchService
from app.services.stats_service import StatsService
from app.services.vehicle_service import VehicleService
from app.utils.logger import get_logger, setup_logging

logger = get_logger("cli")

app = typer.Typer(
    name="vehicle-monitor",
    help="Monitor de anúncios de veículos em marketplaces.",
    no_args_is_help=True,
    add_completion=False,
)

# --- Opções reutilizáveis de filtro -----------------------------------
BrandOpt = Annotated[str | None, typer.Option("--brand", "-b", help="Marca.")]
ModelOpt = Annotated[str | None, typer.Option("--model", "-m", help="Modelo.")]
VersionOpt = Annotated[str | None, typer.Option("--version", help="Versão.")]
YearMinOpt = Annotated[int | None, typer.Option("--year-min", help="Ano mínimo.")]
YearMaxOpt = Annotated[int | None, typer.Option("--year-max", help="Ano máximo.")]
KmMaxOpt = Annotated[int | None, typer.Option("--km-max", help="Km máxima.")]
PriceMinOpt = Annotated[float | None, typer.Option("--price-min", help="Preço mín.")]
PriceMaxOpt = Annotated[float | None, typer.Option("--price-max", help="Preço máx.")]
CityOpt = Annotated[str | None, typer.Option("--city", help="Cidade (define a região no Facebook).")]
StateOpt = Annotated[str | None, typer.Option("--state", help="UF (2 letras).")]
DistanceMaxOpt = Annotated[
    float | None,
    typer.Option("--distance-max", help="Raio em km (aprox.: região da cidade no Facebook)."),
]
FuelOpt = Annotated[str | None, typer.Option("--fuel", help="Combustível.")]
TransOpt = Annotated[str | None, typer.Option("--transmission", help="Câmbio.")]
ColorOpt = Annotated[str | None, typer.Option("--color", help="Cor.")]
SourcesOpt = Annotated[
    list[str] | None,
    typer.Option("--source", "-s", help="Provider(s) a usar. Repita para vários."),
]


@app.callback()
def _main(
    log_level: Annotated[
        str | None, typer.Option("--log-level", help="Nível de log.")
    ] = None,
) -> None:
    """Inicializa logging e garante o schema do banco antes de cada comando."""
    setup_logging(level=log_level)
    init_db()


# ----------------------------------------------------------------------
# db-init
# ----------------------------------------------------------------------
@app.command("db-init")
def db_init() -> None:
    """Cria/atualiza o schema do banco de dados."""
    init_db()
    console.print("[green]Banco inicializado com sucesso.[/green]")


# ----------------------------------------------------------------------
# search
# ----------------------------------------------------------------------
@app.command()
def search(
    brand: BrandOpt = None,
    model: ModelOpt = None,
    version: VersionOpt = None,
    year_min: YearMinOpt = None,
    year_max: YearMaxOpt = None,
    km_max: KmMaxOpt = None,
    price_min: PriceMinOpt = None,
    price_max: PriceMaxOpt = None,
    city: CityOpt = None,
    state: StateOpt = None,
    distance_max: DistanceMaxOpt = None,
    fuel: FuelOpt = None,
    transmission: TransOpt = None,
    color: ColorOpt = None,
    sources: SourcesOpt = None,
    max_results: Annotated[
        int, typer.Option("--max", help="Máximo de anúncios.")
    ] = settings.max_results,
    save: Annotated[
        str | None, typer.Option("--save", help="Salva a busca com este nome.")
    ] = None,
    notify: Annotated[
        bool, typer.Option("--notify", help="Dispara notificações.")
    ] = False,
) -> None:
    """Busca anúncios, persiste e exibe os resultados."""
    vehicle_filter = build_filter(
        brand=brand,
        model=model,
        version=version,
        year_min=year_min,
        year_max=year_max,
        mileage_max=km_max,
        price_min=price_min,
        price_max=price_max,
        city=city,
        state=state,
        distance_max=distance_max,
        fuel=fuel,
        transmission=transmission,
        color=color,
    )

    # Aviso de pré-voo: o Facebook (provider padrão) exige sessão salva.
    effective = sources or default_sources()
    if "facebook" in effective and not settings.facebook_authenticated:
        console.print(
            "[yellow]Atenção:[/yellow] o Facebook Marketplace exige login e "
            "nenhuma sessão foi encontrada. Rode [bold]python main.py login[/bold] "
            "antes de buscar (ou use [bold]--source webmotors[/bold])."
        )

    with console.status("[cyan]Buscando anúncios...[/cyan]"):
        with session_scope() as session:
            monitor = MonitorService(session)
            result = monitor.run_search(
                vehicle_filter,
                sources=sources,
                max_results=max_results,
                notify=notify,
            )
            if save:
                SearchService(session).create(save, vehicle_filter)
            # Veículos persistidos (com ID); attrs seguem acessíveis após
            # o commit graças a expire_on_commit=False.
            persisted = (
                result.report.new_vehicles + result.report.updated_vehicles
                if result.report
                else []
            )

    console.print(
        f"[green]{result.new_count} novos[/green], "
        f"[yellow]{result.price_drop_count} reduções de preço[/yellow]."
    )
    render_vehicles(persisted, title="Resultados da busca")
    if save:
        console.print(f"[blue]Busca salva como {save!r}.[/blue]")


# ----------------------------------------------------------------------
# monitor
# ----------------------------------------------------------------------
@app.command()
def monitor(
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Executar apenas esta busca salva."),
    ] = None,
    interval: Annotated[
        int, typer.Option("--interval", "-i", help="Intervalo em minutos.")
    ] = 30,
    once: Annotated[
        bool, typer.Option("--once", help="Executa apenas uma vez e sai.")
    ] = False,
) -> None:
    """Monitora buscas salvas periodicamente, disparando alertas."""

    def _run_once() -> None:
        with session_scope() as session:
            service = MonitorService(session)
            searches = SearchService(session)
            targets = (
                [searches.get(name)] if name else list(searches.list_active())
            )
            targets = [s for s in targets if s is not None]
            if not targets:
                console.print("[yellow]Nenhuma busca ativa encontrada.[/yellow]")
                return
            for saved in targets:
                result = service.run_saved(saved)
                console.print(
                    f"[bold]{saved.name}[/bold]: {result.new_count} novos, "
                    f"{result.price_drop_count} reduções, "
                    f"{result.notifications_sent} alertas."
                )

    _run_once()
    if once:
        return

    console.print(
        f"[cyan]Monitorando a cada {interval} min. Ctrl+C para sair.[/cyan]"
    )
    schedule.every(interval).minutes.do(_run_once)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - interação manual
        console.print("\n[yellow]Monitoramento encerrado.[/yellow]")


# ----------------------------------------------------------------------
# export
# ----------------------------------------------------------------------
@app.command()
def export(
    fmt: Annotated[
        str, typer.Option("--format", "-f", help="csv | excel | json.")
    ] = "csv",
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Caminho do arquivo.")
    ] = None,
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Filtra por fonte.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Limite de registros.")
    ] = None,
) -> None:
    """Exporta os veículos persistidos para CSV, Excel ou JSON."""
    if fmt.lower() not in available_formats() + ["xlsx"]:
        console.print(
            f"[red]Formato inválido. Use: {', '.join(available_formats())}.[/red]"
        )
        raise typer.Exit(code=1)

    with session_scope() as session:
        vehicles = list(
            VehicleService(session).list_vehicles(source=source, limit=limit)
        )
        path = None
        if vehicles:
            path = get_exporter(fmt).export(vehicles, path=output)

    if not vehicles:
        console.print("[yellow]Nenhum veículo para exportar.[/yellow]")
        raise typer.Exit(code=0)
    console.print(f"[green]{len(vehicles)} veículos exportados para {path}.[/green]")


# ----------------------------------------------------------------------
# stats
# ----------------------------------------------------------------------
@app.command()
def stats() -> None:
    """Exibe estatísticas agregadas do banco de dados."""
    with session_scope() as session:
        render_stats(StatsService(session).compute())


# ----------------------------------------------------------------------
# list
# ----------------------------------------------------------------------
@app.command("list")
def list_vehicles(
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Filtra por fonte.")
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Máx. de anúncios.")
    ] = 30,
) -> None:
    """Lista os anúncios já salvos (com ID e link clicável)."""
    with session_scope() as session:
        vehicles = list(
            VehicleService(session).list_vehicles(source=source, limit=limit)
        )
    if not vehicles:
        console.print("[yellow]Nenhum anúncio salvo. Rode uma busca antes.[/yellow]")
        return
    render_vehicles(vehicles, title="Anúncios salvos")


# ----------------------------------------------------------------------
# open
# ----------------------------------------------------------------------
@app.command("open")
def open_listing(
    vehicle_id: Annotated[int, typer.Argument(help="ID do anúncio (veja em list).")],
    print_only: Annotated[
        bool, typer.Option("--print", help="Apenas imprime a URL, não abre.")
    ] = False,
) -> None:
    """Abre o anúncio de um veículo (pelo ID) no navegador padrão."""
    url: str | None = None
    title: str | None = None
    with session_scope() as session:
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is not None:
            url, title = vehicle.url, vehicle.title

    if url is None:
        console.print(f"[red]Anúncio {vehicle_id} não encontrado.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]{title}[/bold]\n[link={url}]{url}[/link]")
    if not print_only:
        import webbrowser

        webbrowser.open(url)
        console.print("[green]Abrindo no navegador...[/green]")


# ----------------------------------------------------------------------
# providers
# ----------------------------------------------------------------------
@app.command()
def providers() -> None:
    """Lista os providers (marketplaces) disponíveis."""
    console.print("[bold]Providers disponíveis:[/bold]")
    for source in available_providers():
        console.print(f"  • {source}")


@app.command()
def login(
    url: Annotated[
        str, typer.Option("--url", help="Página de login a abrir.")
    ] = "https://www.facebook.com/login",
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Arquivo de sessão a salvar."),
    ] = None,
) -> None:
    """Abre um navegador para login manual e salva a sessão (cookies).

    O Facebook Marketplace exige autenticação. Rode este comando uma vez,
    faça login na janela que abrir e a sessão será reutilizada nas buscas.
    """
    from app.providers.browser import BrowserManager

    destination = output or settings.facebook_auth_state
    console.print(
        "[cyan]Abrindo navegador para login...[/cyan] "
        "Faça login e [bold]volte aqui[/bold]."
    )
    # Sempre com janela visível — o login é manual.
    manager = BrowserManager(headless=False, navigation_timeout=120_000)
    manager.start()
    try:
        with manager.new_page() as page:
            page.goto(url, wait_until="domcontentloaded")
            typer.prompt(
                "Pressione ENTER aqui depois de concluir o login no navegador",
                default="",
                show_default=False,
            )
            path = manager.save_storage_state(destination)
    finally:
        manager.stop()
    console.print(f"[green]Sessão salva em {path}.[/green]")
