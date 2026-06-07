"""Canal de notificação via Discord Webhook."""

from __future__ import annotations

import requests

from app.config import settings
from app.exceptions import NotificationError
from app.models.enums import NotificationChannel
from app.notifications.base import NotificationMessage, NotificationProvider

_TIMEOUT = 15


class DiscordNotifier(NotificationProvider):
    """Envia mensagens para um canal do Discord via *webhook*."""

    channel = NotificationChannel.DISCORD

    def is_enabled(self) -> bool:
        return settings.discord_enabled

    def _deliver(self, message: NotificationMessage) -> None:
        embed = {
            "title": message.title,
            "description": message.body,
            "url": message.url,
        }
        payload = {"embeds": [embed]}
        try:
            response = requests.post(
                str(settings.discord_webhook), json=payload, timeout=_TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NotificationError(f"Discord: {exc}") from exc
