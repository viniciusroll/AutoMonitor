"""Modelos de domínio (ORM) e DTOs.

Importar este pacote registra todos os modelos na ``Base.metadata``,
o que é essencial para a criação automática do schema em ``init_db``.
"""

from __future__ import annotations

from app.models.enums import (
    FuelType,
    NotificationChannel,
    NotificationEvent,
    SellerType,
    TransmissionType,
)
from app.models.notification import Notification
from app.models.price_history import PriceHistory
from app.models.search import Search
from app.models.vehicle import ScrapedVehicle, Vehicle

__all__ = [
    # Enums
    "FuelType",
    "TransmissionType",
    "SellerType",
    "NotificationChannel",
    "NotificationEvent",
    # ORM
    "Vehicle",
    "PriceHistory",
    "Search",
    "Notification",
    # DTOs
    "ScrapedVehicle",
]
