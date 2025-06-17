"""Sensor zur PV-Gesamtproduktion in kWh.

Dieser Sensor summiert die PV-Produktion insgesamt.
"""

from homeassistant.core import HomeAssistant

from .total_integral_sensor import TotalIntegralSensor


class PvTotalEnergy(TotalIntegralSensor):
    """Sensor zur Integration der PV-Produktionsleistung (kWh gesamt)."""

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den täglichen PV-Energieproduktionssensor.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz der Integration.
            source_entity_id (str): Die Entity-ID der Quell-Leistungs-Sensorentität.

        """
        super().__init__(hass, entry, source_entity_id)
