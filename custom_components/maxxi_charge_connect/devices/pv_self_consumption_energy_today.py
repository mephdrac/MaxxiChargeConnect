"""Sensor zur täglichen Integration des PV-Eigenverbrauchs in kWh.

Dieser Sensor summiert die PV-Eigenverbrauchsleistung über den Tag
und setzt den Wert täglich um Mitternacht lokal zurück.
"""

from .today_integral_sensor import TodayIntegralSensor


class PvSelfConsumptionEnergyToday(TodayIntegralSensor):
    """Sensor zur Integration der PV-Eigenverbrauchsleistung (kWh heute)."""
    _attr_entity_registry_enabled_default = False
