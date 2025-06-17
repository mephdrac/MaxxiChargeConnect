"""Sensor zur täglichen Integration des PV-Eigenverbrauchs in kWh.

Dieser Sensor summiert die PV-Eigenverbrauchsleistung über den Tag
und setzt den Wert täglich um Mitternacht lokal zurück.
"""

from homeassistant.core import HomeAssistant

from .today_integral_sensor import TodayIntegralSensor


class PvSelfConsumptionEnergyToday(TodayIntegralSensor):
    """Sensor zur Integration der PV-Eigenverbrauchsleistung (kWh heute)."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den täglichen PV-Energieverbrauchssensor.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz der Integration.
            source_entity_id (str): Die Entity-ID der Quell-Leistungs-Sensorentität.

        """
        super().__init__(hass, entry, source_entity_id)
