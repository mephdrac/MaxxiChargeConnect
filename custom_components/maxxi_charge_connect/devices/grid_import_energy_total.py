"""Sensor zur Gesamtmessung der importierten Energie aus dem Stromnetz.

Dieses Modul stellt die Entität `GridImportEnergyTotal` zur Verfügung, die
mithilfe eines Leistungssensors (z. B. Netzbezug) kontinuierlich die
importierte Energie in kWh summiert. Die Werte steigen dauerhaft an
(TOTAL_INCREASING).
"""

from homeassistant.core import HomeAssistant

from .total_integral_sensor import TotalIntegralSensor


class GridImportEnergyTotal(TotalIntegralSensor):
    """Sensor-Entität zur Messung der insgesamt importierten Energie.

    Verwendet die IntegrationSensor-Funktionalität von Home Assistant, um
    kontinuierlich Energie (kWh) auf Basis eines Quell-Leistungssensors zu
    integrieren. Die gemessene Energie steigt monoton an (TOTAL_INCREASING).
    """

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den Sensor zur Erfassung der Gesamtenergie aus dem Netz.

        Args:
            hass (HomeAssistant): Die zentrale Home Assistant Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.
            source_entity_id (str): Die Entity-ID des Quellsensors (z. B. Netzimportleistung).

        """
        super().__init__(hass, entry, source_entity_id)
