"""Sensor zur täglichen Integration des Eigenverbrauchs in kWh.

Dieser Sensor summiert die gesamte Eigenverbrauchsleistung.
"""

from .total_integral_sensor import TotalIntegralSensor


class ConsumptionEnergyTotal(TotalIntegralSensor):
    """Sensor zur Integration der Eigenverbrauchsleistung (kWh gesamt)."""

    _attr_entity_registry_enabled_default = False
