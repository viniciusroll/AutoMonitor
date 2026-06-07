"""Canal de notificação via Email (SMTP)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.exceptions import NotificationError
from app.models.enums import NotificationChannel
from app.notifications.base import NotificationMessage, NotificationProvider

_TIMEOUT = 20


class EmailNotifier(NotificationProvider):
    """Envia mensagens por email usando SMTP com STARTTLS."""

    channel = NotificationChannel.EMAIL

    def is_enabled(self) -> bool:
        return settings.email_enabled

    def _deliver(self, message: NotificationMessage) -> None:
        email = EmailMessage()
        email["Subject"] = f"[Vehicle Monitor] {message.title}"
        email["From"] = settings.email_user
        email["To"] = settings.email_to
        email.set_content(message.as_text())

        try:
            with smtplib.SMTP(
                settings.email_smtp_host,
                settings.email_smtp_port,
                timeout=_TIMEOUT,
            ) as server:
                server.starttls()
                server.login(
                    str(settings.email_user), str(settings.email_password)
                )
                server.send_message(email)
        except (smtplib.SMTPException, OSError) as exc:
            raise NotificationError(f"Email: {exc}") from exc
