"""Sensor zur täglichen Integration des PV-Produktion in kWh.

Dieser Sensor summiert die PV-Produktion über den Tag
und setzt den Wert täglich um Mitternacht lokal zurück.
"""

from .today_integral_sensor import TodayIntegralSensor


class PvTodayEnergy(TodayIntegralSensor):
    """Sensor zur Integration der PV-Produktionsleistung (kWh heute)."""
