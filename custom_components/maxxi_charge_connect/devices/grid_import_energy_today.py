"""Sensor zur Messung der heute importierten Energie aus dem Stromnetz für Home Assistant.

Dieses Modul definiert die Entität `GridImportEnergyToday`, die auf Basis
eines Leistungssensors kontinuierlich die importierte Energie integriert und
täglich um Mitternacht zurücksetzt.
"""

from homeassistant.core import HomeAssistant

from .today_integral_sensor import TodayIntegralSensor


class GridImportEnergyToday(TodayIntegralSensor):
    """Sensor-Entität zur Erfassung der importierten Energie (heute).

    Verwendet die IntegrationSensor-Funktionalität von Home Assistant,
    um kontinuierlich Energie (kWh) basierend auf einem Quell-Leistungssensor
    über den Tag hinweg zu integrieren. Die Energie wird täglich um 0:00 Uhr
    lokale Zeit zurückgesetzt.
    """

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den Sensor für importierte Tagesenergie.

        Args:
            hass (HomeAssistant): Die zentrale Home Assistant Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.
            source_entity_id (str): Die Entity-ID des Quellsensors (z. B. Netzimportleistung).

        """

        super().__init__(hass, entry, source_entity_id)
