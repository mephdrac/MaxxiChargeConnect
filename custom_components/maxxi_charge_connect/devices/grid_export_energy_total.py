"""IntegrationSensor zur Erfassung der insgesamt exportierten Energie ins Netz.

Diese Entität berechnet auf Basis eines Quell-Sensors (z. B. Momentanleistung)
die exportierte Energie ins Stromnetz über die Zeit. Sie verwendet dafür die
trapezförmige Integrationsmethode und speichert das Ergebnis als kumulativen Zähler.

Die Einheit der Messung ist Kilowattstunden (kWh).
"""

from homeassistant.core import HomeAssistant

from .total_integral_sensor import TotalIntegralSensor


class GridExportEnergyTotal(TotalIntegralSensor):
    """Sensor zur Berechnung der gesamten Netzeinspeisung (kWh)."""

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Entität für Netzeinspeisung gesamt.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfiguration der Integration.
            source_entity_id (str): Die Entity ID des Leistungssensors, der integriert werden soll.

        """

        super().__init__(hass, entry, source_entity_id)
