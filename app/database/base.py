"""Configuração do engine, sessão e base declarativa do SQLAlchemy.

Implementa também a criação automática do schema (``init_db``), que
funciona como uma "migration" simples baseada em ``metadata.create_all``,
adequada ao escopo do projeto (SQLite).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings
from app.exceptions import DatabaseError
from app.utils.logger import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos ORM."""


# ``check_same_thread=False`` permite uso em contextos multi-thread
# (ex.: scheduler). ``future=True`` é o padrão no SQLAlchemy 2.0.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine: Engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
    """Habilita verificação de chaves estrangeiras no SQLite."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:  # pragma: no cover - backends não-SQLite
        pass


def init_db() -> None:
    """Cria todas as tabelas declaradas (migration automática).

    É seguro chamar múltiplas vezes: tabelas já existentes são ignoradas.

    Raises:
        DatabaseError: se a criação do schema falhar.
    """
    # Import tardio garante que todos os modelos sejam registrados na
    # ``Base.metadata`` antes do ``create_all``.
    from app import models  # noqa: F401  (efeito colateral de registro)

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Schema do banco verificado/criado com sucesso.")
    except Exception as exc:  # pragma: no cover - falha de infra
        raise DatabaseError(f"Falha ao inicializar o banco: {exc}") from exc


def get_session() -> Session:
    """Retorna uma nova sessão (o chamador é responsável por fechá-la)."""
    return SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager transacional.

    Faz commit ao final do bloco; em caso de exceção, faz rollback e
    re-levanta. Sempre fecha a sessão.

    Example:
        >>> with session_scope() as session:
        ...     session.add(obj)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Transação revertida: {exc}")
        raise
    finally:
        session.close()
