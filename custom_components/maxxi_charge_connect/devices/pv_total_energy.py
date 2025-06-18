"""Sensor zur PV-Gesamtproduktion in kWh.

Dieser Sensor summiert die PV-Produktion insgesamt.
"""

from .total_integral_sensor import TotalIntegralSensor


class PvTotalEnergy(TotalIntegralSensor):
    """Sensor zur Integration der PV-Produktionsleistung (kWh gesamt)."""
