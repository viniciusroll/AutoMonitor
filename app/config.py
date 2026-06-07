"""Configuração centralizada da aplicação.

Carrega variáveis de ambiente a partir de um arquivo ``.env`` (ou do
ambiente do sistema) e as expõe de forma tipada e validada usando
``pydantic-settings``.

A instância única :data:`settings` deve ser importada onde necessário::

    from app.config import settings

    if settings.headless:
        ...
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (…/market_place_finder)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Diretórios de saída garantidos em tempo de import.
LOGS_DIR: Path = BASE_DIR / "logs"
EXPORTS_DIR: Path = BASE_DIR / "exports"


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do ambiente / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Banco de dados ---
    database_url: str = Field(
        default="sqlite:///vehicle_monitor.db",
        description="URL de conexão no formato SQLAlchemy.",
    )

    # --- Playwright ---
    headless: bool = Field(default=True)
    max_results: int = Field(default=100, ge=1, le=10_000)
    navigation_timeout: int = Field(default=30_000, ge=1_000)

    # --- Telegram ---
    telegram_token: str | None = Field(default=None)
    telegram_chat_id: str | None = Field(default=None)

    # --- Discord ---
    discord_webhook: str | None = Field(default=None)

    # --- Email (SMTP) ---
    email_user: str | None = Field(default=None)
    email_password: str | None = Field(default=None)
    email_smtp_host: str = Field(default="smtp.gmail.com")
    email_smtp_port: int = Field(default=587, ge=1, le=65_535)
    email_to: str | None = Field(default=None)

    # --- Logs ---
    log_level: str = Field(default="INFO")

    # ------------------------------------------------------------------
    # Validadores
    # ------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        valid = {
            "TRACE",
            "DEBUG",
            "INFO",
            "SUCCESS",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }
        upper = value.upper()
        if upper not in valid:
            raise ValueError(
                f"LOG_LEVEL inválido: {value!r}. Use um de {sorted(valid)}."
            )
        return upper

    @field_validator("telegram_token", "telegram_chat_id", "discord_webhook",
                     "email_user", "email_password", "email_to", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: object) -> object:
        """Trata strings vazias do ``.env`` como ``None``."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    # ------------------------------------------------------------------
    # Conveniências
    # ------------------------------------------------------------------
    @property
    def logs_dir(self) -> Path:
        return LOGS_DIR

    @property
    def exports_dir(self) -> Path:
        return EXPORTS_DIR

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook)

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_user and self.email_password and self.email_to)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância única de :class:`Settings` (cacheada)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()


# Instância global de conveniência.
settings: Settings = get_settings()
