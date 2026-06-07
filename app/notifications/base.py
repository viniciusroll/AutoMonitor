"""Interface comum dos canais de notificação.

:class:`NotificationProvider` desacopla a regra de negócio do meio de
entrega (Telegram, Discord, Email…). Novos canais podem ser adicionados
implementando esta interface, sem alterar os serviços que disparam os
alertas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import NotificationChannel, NotificationEvent
from app.models.vehicle import Vehicle
from app.utils.logger import get_logger


@dataclass(slots=True)
class NotificationMessage:
    """Mensagem normalizada a ser enviada por um canal."""

    event: NotificationEvent
    title: str
    body: str
    url: str | None = None
    vehicle_id: int | None = None

    def as_text(self) -> str:
        """Renderiza a mensagem como texto simples (com URL ao final)."""
        parts = [self.title, "", self.body]
        if self.url:
            parts.extend(["", self.url])
        return "\n".join(parts)


def build_message(
    event: NotificationEvent, vehicle: Vehicle, *, extra: str | None = None
) -> NotificationMessage:
    """Cria uma :class:`NotificationMessage` a partir de um veículo."""
    headers = {
        NotificationEvent.NEW_VEHICLE: "🆕 Novo anúncio encontrado",
        NotificationEvent.PRICE_DROP: "📉 Redução de preço",
        NotificationEvent.MATCH: "🎯 Veículo dentro dos critérios",
    }
    price = f"R$ {vehicle.price:,.0f}".replace(",", ".") if vehicle.price else "—"
    location = " - ".join(p for p in (vehicle.city, vehicle.state) if p) or "—"
    lines = [
        f"{vehicle.title}",
        f"Preço: {price}",
        f"Ano: {vehicle.year or '—'} | Km: {vehicle.mileage or '—'}",
        f"Local: {location}",
        f"Fonte: {vehicle.source}",
    ]
    if extra:
        lines.append(extra)
    return NotificationMessage(
        event=event,
        title=headers.get(event, "Alerta"),
        body="\n".join(lines),
        url=vehicle.url,
        vehicle_id=vehicle.id,
    )


class NotificationProvider(ABC):
    """Contrato comum a todos os canais de notificação."""

    #: Canal associado a este provider.
    channel: NotificationChannel

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def is_enabled(self) -> bool:
        """Indica se o canal está corretamente configurado/ativo."""

    @abstractmethod
    def _deliver(self, message: NotificationMessage) -> None:
        """Envia a mensagem pelo canal (pode lançar :class:`NotificationError`)."""

    def send(self, message: NotificationMessage) -> bool:
        """Envia a mensagem se o canal estiver habilitado.

        Returns:
            ``True`` em caso de sucesso; ``False`` se desabilitado ou erro.
        """
        if not self.is_enabled():
            self.logger.debug(f"Canal {self.channel.value} desabilitado; ignorando.")
            return False
        try:
            self._deliver(message)
            self.logger.info(
                f"Notificação enviada via {self.channel.value} "
                f"({message.event.value})."
            )
            return True
        except Exception as exc:
            self.logger.error(
                f"Falha ao enviar via {self.channel.value}: {exc}"
            )
            return False
