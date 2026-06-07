"""Canal de notificação via Telegram Bot API."""

from __future__ import annotations

import requests

from app.config import settings
from app.exceptions import NotificationError
from app.models.enums import NotificationChannel
from app.notifications.base import NotificationMessage, NotificationProvider

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 15


class TelegramNotifier(NotificationProvider):
    """Envia mensagens para um chat do Telegram via *bot*."""

    channel = NotificationChannel.TELEGRAM

    def is_enabled(self) -> bool:
        return settings.telegram_enabled

    def _deliver(self, message: NotificationMessage) -> None:
        url = _API_URL.format(token=settings.telegram_token)
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": message.as_text(),
            "disable_web_page_preview": False,
        }
        try:
            response = requests.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NotificationError(f"Telegram: {exc}") from exc
