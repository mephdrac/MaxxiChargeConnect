"""Grid Export Energy Sensor für Home Assistant.

Dieses Modul enthält die Klasse `GridExportEnergyToday`, einen spezialisierten
IntegrationSensor, der die heute exportierte Energie ins Stromnetz misst.

Die Energie wird täglich um Mitternacht (lokale Zeit) zurückgesetzt.
"""

from homeassistant.core import HomeAssistant

from .today_integral_sensor import TodayIntegralSensor


class GridExportEnergyToday(TodayIntegralSensor):
    """Sensor für die täglich exportierte Energie ins Stromnetz.

    Nutzt die IntegrationSensor-Basisfunktionalität von Home Assistant,
    um kontinuierlich Energie über Zeit zu integrieren (Wh), die von einem
    Quellsensor stammt (z. B. Leistungssensor).

    Die Energie wird täglich um Mitternacht zurückgesetzt.
    """

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den Sensor für die exportierte Energie.

        Args:
            hass (HomeAssistant): Die zentrale Home Assistant Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.
            source_entity_id (str): Die Entity-ID des Quellsensors (z. B. Leistung).

        """
        super().__init__(hass, entry, source_entity_id)
