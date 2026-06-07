"""Ponto de entrada da aplicação Vehicle Monitor.

Executa a CLI Typer::

    python main.py search --brand "Honda" --model "Civic" --year-min 2018
    python main.py monitor --interval 30
    python main.py export --format excel
    python main.py stats
"""

from __future__ import annotations

from app.cli import app


def main() -> None:
    """Inicia a aplicação de linha de comando."""
    app()


if __name__ == "__main__":
    main()
