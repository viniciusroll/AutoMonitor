"""Enumerações de domínio compartilhadas."""

from __future__ import annotations

from enum import Enum


class SellerType(str, Enum):
    """Tipo de vendedor do anúncio."""

    PARTICULAR = "particular"
    LOJA = "loja"
    DESCONHECIDO = "desconhecido"


class FuelType(str, Enum):
    """Tipo de combustível."""

    FLEX = "flex"
    GASOLINA = "gasolina"
    ETANOL = "etanol"
    DIESEL = "diesel"
    GNV = "gnv"
    HIBRIDO = "hibrido"
    ELETRICO = "eletrico"
    DESCONHECIDO = "desconhecido"


class TransmissionType(str, Enum):
    """Tipo de câmbio."""

    MANUAL = "manual"
    AUTOMATICO = "automatico"
    AUTOMATIZADO = "automatizado"
    CVT = "cvt"
    DESCONHECIDO = "desconhecido"


class NotificationChannel(str, Enum):
    """Canais de notificação suportados."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"


class NotificationEvent(str, Enum):
    """Eventos que disparam uma notificação."""

    NEW_VEHICLE = "new_vehicle"
    PRICE_DROP = "price_drop"
    MATCH = "match"
