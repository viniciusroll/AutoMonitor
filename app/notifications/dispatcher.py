"""Orquestrador de envio de notificações por múltiplos canais.

O :class:`NotificationDispatcher` recebe um evento + veículo, envia por
todos os canais habilitados e registra cada tentativa na tabela
``notifications`` (auditoria).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.enums import NotificationEvent
from app.models.notification import Notification
from app.models.vehicle import Vehicle
from app.notifications.base import (
    NotificationMessage,
    NotificationProvider,
    build_message,
)
from app.notifications.discord import DiscordNotifier
from app.notifications.email import EmailNotifier
from app.notifications.telegram import TelegramNotifier
from app.utils.logger import get_logger

logger = get_logger("dispatcher")


def default_providers() -> list[NotificationProvider]:
    """Retorna a lista padrão de canais (todos os implementados)."""
    return [TelegramNotifier(), DiscordNotifier(), EmailNotifier()]


class NotificationDispatcher:
    """Dispara notificações por todos os canais habilitados."""

    def __init__(
        self,
        providers: Sequence[NotificationProvider] | None = None,
        *,
        session: Session | None = None,
    ) -> None:
        self._providers = list(providers) if providers is not None else default_providers()
        self._session = session

    @property
    def enabled_channels(self) -> list[str]:
        """Lista dos canais atualmente habilitados."""
        return [p.channel.value for p in self._providers if p.is_enabled()]

    def notify(
        self, event: NotificationEvent, vehicle: Vehicle, *, extra: str | None = None
    ) -> int:
        """Envia o alerta de ``event`` para ``vehicle`` por todos os canais.

        Returns:
            Quantidade de canais que entregaram com sucesso.
        """
        message = build_message(event, vehicle, extra=extra)
        return self.dispatch(message)

    def dispatch(self, message: NotificationMessage) -> int:
        """Envia uma mensagem já construída; registra a auditoria."""
        successes = 0
        for provider in self._providers:
            if not provider.is_enabled():
                continue
            ok = provider.send(message)
            successes += int(ok)
            self._record(provider, message, success=ok)
        if not self._providers or successes == 0:
            logger.debug("Nenhum canal habilitado ou nenhuma entrega bem-sucedida.")
        return successes

    # ------------------------------------------------------------------
    def _record(
        self,
        provider: NotificationProvider,
        message: NotificationMessage,
        *,
        success: bool,
    ) -> None:
        if self._session is None:
            return
        record = Notification(
            vehicle_id=message.vehicle_id,
            channel=provider.channel.value,
            event=message.event.value,
            message=message.as_text(),
            success=success,
            error=None if success else "envio falhou",
        )
        try:
            self._session.add(record)
            self._session.flush()
        except Exception as exc:  # pragma: no cover - auditoria best-effort
            logger.warning(f"Falha ao registrar auditoria de notificação: {exc}")
