"""Sensor zur täglichen Integration des PV-Eigenverbrauchs in kWh.

Dieser Sensor summiert die PV-Eigenverbrauchsleistung insgesamt.
"""

from homeassistant.core import HomeAssistant

from .total_integral_sensor import TotalIntegralSensor


class PvSelfConsumptionEnergyTotal(TotalIntegralSensor):
    """Sensor zur Integration der PV-Eigenverbrauchsleistung (kWh gesamt)."""

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den täglichen PV-Energieverbrauchssensor.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz der Integration.
            source_entity_id (str): Die Entity-ID der Quell-Leistungs-Sensorentität.

        """
        super().__init__(hass, entry, source_entity_id)
