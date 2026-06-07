"""Fixtures compartilhadas dos testes.

Cria um banco SQLite em memória isolado por teste, reaproveitando os
modelos declarados em :data:`app.database.base.Base`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.vehicle import ScrapedVehicle

# Importa os modelos para registrá-los em Base.metadata.
import app.models  # noqa: F401


@pytest.fixture()
def session() -> Iterator[Session]:
    """Sessão transacional sobre um banco em memória, descartado ao final."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    try:
        yield db
        db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def scraped_factory():
    """Fábrica de :class:`ScrapedVehicle` com valores padrão sobrescrevíveis."""

    def _make(**overrides: object) -> ScrapedVehicle:
        data: dict[str, object] = {
            "source": "webmotors",
            "external_id": "100",
            "url": "https://www.webmotors.com.br/carro/100",
            "title": "Honda Civic EXL 2019",
            "brand": "Honda",
            "model": "Civic",
            "year": 2019,
            "mileage": 45_000,
            "price": 95_000.0,
            "city": "São Paulo",
            "state": "SP",
        }
        data.update(overrides)
        return ScrapedVehicle(**data)  # type: ignore[arg-type]

    return _make
