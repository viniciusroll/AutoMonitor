"""Testes do sistema de notificações (sem rede)."""

from __future__ import annotations

from app.models.enums import NotificationChannel, NotificationEvent
from app.models.notification import Notification
from app.notifications.base import (
    NotificationMessage,
    NotificationProvider,
    build_message,
)
from app.notifications.dispatcher import NotificationDispatcher
from app.services.vehicle_service import VehicleService


class FakeNotifier(NotificationProvider):
    """Canal de teste que apenas registra as mensagens entregues."""

    channel = NotificationChannel.TELEGRAM

    def __init__(self, *, enabled: bool = True, fail: bool = False) -> None:
        super().__init__()
        self._enabled = enabled
        self._fail = fail
        self.sent: list[NotificationMessage] = []

    def is_enabled(self) -> bool:
        return self._enabled

    def _deliver(self, message: NotificationMessage) -> None:
        if self._fail:
            raise RuntimeError("boom")
        self.sent.append(message)


def _vehicle(session, scraped_factory):
    service = VehicleService(session)
    report = service.save_many([scraped_factory()])
    return report.new_vehicles[0]


def test_build_message_contem_dados_do_veiculo(session, scraped_factory) -> None:
    vehicle = _vehicle(session, scraped_factory)
    message = build_message(NotificationEvent.NEW_VEHICLE, vehicle)
    assert "Honda Civic" in message.body
    assert message.url == vehicle.url
    assert message.event is NotificationEvent.NEW_VEHICLE


def test_dispatcher_envia_por_canais_habilitados(session, scraped_factory) -> None:
    vehicle = _vehicle(session, scraped_factory)
    notifier = FakeNotifier(enabled=True)
    dispatcher = NotificationDispatcher([notifier], session=session)
    enviados = dispatcher.notify(NotificationEvent.NEW_VEHICLE, vehicle)
    assert enviados == 1
    assert len(notifier.sent) == 1


def test_dispatcher_ignora_canal_desabilitado(session, scraped_factory) -> None:
    vehicle = _vehicle(session, scraped_factory)
    dispatcher = NotificationDispatcher([FakeNotifier(enabled=False)], session=session)
    assert dispatcher.notify(NotificationEvent.NEW_VEHICLE, vehicle) == 0


def test_dispatcher_registra_auditoria(session, scraped_factory) -> None:
    vehicle = _vehicle(session, scraped_factory)
    dispatcher = NotificationDispatcher([FakeNotifier(enabled=True)], session=session)
    dispatcher.notify(NotificationEvent.NEW_VEHICLE, vehicle)
    registros = session.query(Notification).all()
    assert len(registros) == 1
    assert registros[0].success is True


def test_falha_no_envio_e_registrada_como_insucesso(session, scraped_factory) -> None:
    vehicle = _vehicle(session, scraped_factory)
    dispatcher = NotificationDispatcher(
        [FakeNotifier(enabled=True, fail=True)], session=session
    )
    assert dispatcher.notify(NotificationEvent.NEW_VEHICLE, vehicle) == 0
    registro = session.query(Notification).one()
    assert registro.success is False
