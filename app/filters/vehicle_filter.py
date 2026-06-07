"""Filtro configurável de veículos.

:class:`VehicleFilter` encapsula todos os critérios de filtragem
suportados e sabe avaliar se um veículo (DTO :class:`ScrapedVehicle`
ou ORM :class:`Vehicle`) atende a esses critérios.

O filtro é serializável (``to_dict`` / ``from_dict``) para ser
persistido no campo JSON de uma :class:`Search`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import FuelType, TransmissionType


def _norm(value: str | None) -> str | None:
    """Normaliza string para comparação (minúscula, sem espaços nas pontas)."""
    if value is None:
        return None
    value = value.strip().lower()
    return value or None


class VehicleFilter(BaseModel):
    """Conjunto de critérios para filtrar anúncios de veículos.

    Todos os campos são opcionais; ausência significa "sem restrição".
    Comparações de texto são *case-insensitive* e por substring, exceto
    ``state`` (igualdade exata da sigla) e os enums ``fuel`` e
    ``transmission``.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    # Texto livre
    brand: str | None = None
    model: str | None = None
    version: str | None = None
    color: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)

    # Faixas numéricas
    year_min: int | None = Field(default=None, ge=1900, le=2100)
    year_max: int | None = Field(default=None, ge=1900, le=2100)
    mileage_max: int | None = Field(default=None, ge=0)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    distance_max: float | None = Field(default=None, ge=0)

    # Enums
    fuel: FuelType | None = None
    transmission: TransmissionType | None = None

    # ------------------------------------------------------------------
    # Validação de coerência das faixas
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_ranges(self) -> "VehicleFilter":
        if (
            self.year_min is not None
            and self.year_max is not None
            and self.year_min > self.year_max
        ):
            raise ValueError("year_min não pode ser maior que year_max.")
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min não pode ser maior que price_max.")
        return self

    # ------------------------------------------------------------------
    # Avaliação
    # ------------------------------------------------------------------
    def matches(self, vehicle: Any) -> bool:
        """Indica se ``vehicle`` satisfaz todos os critérios definidos.

        Funciona tanto com :class:`ScrapedVehicle` quanto com o ORM
        :class:`Vehicle`, acessando atributos por ``getattr``. Campos do
        veículo ausentes (``None``) não eliminam o veículo, exceto quando
        o próprio critério exige um valor (ex.: ``price_max`` com preço
        desconhecido => não passa).
        """
        checks = (
            self._match_text(vehicle, "brand", self.brand),
            self._match_text(vehicle, "model", self.model),
            self._match_text(vehicle, "version", self.version),
            self._match_text(vehicle, "color", self.color),
            self._match_text(vehicle, "city", self.city),
            self._match_state(vehicle),
            self._match_year(vehicle),
            self._match_mileage(vehicle),
            self._match_price(vehicle),
            self._match_enum(vehicle, "fuel", self.fuel),
            self._match_enum(vehicle, "transmission", self.transmission),
        )
        return all(checks)

    # --- helpers individuais -------------------------------------------------
    @staticmethod
    def _match_text(vehicle: Any, attr: str, expected: str | None) -> bool:
        if expected is None:
            return True
        actual = _norm(getattr(vehicle, attr, None))
        if actual is None:
            return False
        return _norm(expected) in actual  # type: ignore[operator]

    def _match_state(self, vehicle: Any) -> bool:
        if self.state is None:
            return True
        actual = getattr(vehicle, "state", None)
        if not actual:
            return False
        return actual.strip().upper() == self.state.strip().upper()

    def _match_year(self, vehicle: Any) -> bool:
        year = getattr(vehicle, "year", None)
        if self.year_min is not None:
            if year is None or year < self.year_min:
                return False
        if self.year_max is not None:
            if year is None or year > self.year_max:
                return False
        return True

    def _match_mileage(self, vehicle: Any) -> bool:
        if self.mileage_max is None:
            return True
        mileage = getattr(vehicle, "mileage", None)
        if mileage is None:
            return False
        return mileage <= self.mileage_max

    def _match_price(self, vehicle: Any) -> bool:
        price = getattr(vehicle, "price", None)
        if self.price_min is not None:
            if price is None or price < self.price_min:
                return False
        if self.price_max is not None:
            if price is None or price > self.price_max:
                return False
        return True

    @staticmethod
    def _match_enum(vehicle: Any, attr: str, expected: Any) -> bool:
        if expected is None:
            return True
        actual = getattr(vehicle, attr, None)
        if actual is None:
            return False
        expected_value = expected.value if hasattr(expected, "value") else expected
        actual_value = actual.value if hasattr(actual, "value") else actual
        return str(actual_value).lower() == str(expected_value).lower()

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serializa o filtro para dict (apenas campos definidos)."""
        return self.model_dump(exclude_none=True, mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VehicleFilter":
        """Reconstrói um filtro a partir de um dict (ex.: campo JSON)."""
        return cls.model_validate(data or {})

    def describe(self) -> str:
        """Resumo legível dos critérios ativos (para logs/CLI)."""
        active = self.to_dict()
        if not active:
            return "sem filtros"
        return ", ".join(f"{k}={v}" for k, v in active.items())
