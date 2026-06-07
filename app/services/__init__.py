"""Casos de uso / orquestração da aplicação."""

from __future__ import annotations

from app.services.monitor_service import MonitorService, RunResult
from app.services.search_service import SearchService
from app.services.stats_service import Stats, StatsService
from app.services.vehicle_service import (
    PriceDrop,
    SaveReport,
    VehicleService,
)

__all__ = [
    "MonitorService",
    "RunResult",
    "SearchService",
    "StatsService",
    "Stats",
    "VehicleService",
    "SaveReport",
    "PriceDrop",
]
