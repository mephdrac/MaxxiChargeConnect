"""Sensor zur täglichen Integration des PV-Eigenverbrauchs in kWh.

Dieser Sensor summiert die PV-Eigenverbrauchsleistung insgesamt.
"""

from .total_integral_sensor import TotalIntegralSensor


class PvSelfConsumptionEnergyTotal(TotalIntegralSensor):
    """Sensor zur Integration der PV-Eigenverbrauchsleistung (kWh gesamt)."""

    _attr_entity_registry_enabled_default = False
