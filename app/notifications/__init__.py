"""Canais de notificação desacoplados (Telegram, Discord, Email)."""

from __future__ import annotations

from app.notifications.base import (
    NotificationMessage,
    NotificationProvider,
    build_message,
)
from app.notifications.discord import DiscordNotifier
from app.notifications.dispatcher import NotificationDispatcher, default_providers
from app.notifications.email import EmailNotifier
from app.notifications.telegram import TelegramNotifier

__all__ = [
    "NotificationProvider",
    "NotificationMessage",
    "build_message",
    "TelegramNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "NotificationDispatcher",
    "default_providers",
]
