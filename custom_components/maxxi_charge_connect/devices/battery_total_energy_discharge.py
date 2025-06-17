"""Sensor für die gesamte Batterieentladeenergie (BatteryTotalEnergyDischarge).

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte aus der Batterie entnommene Energie über die Zeit aufsummiert.

Die Energiemenge wird mittels der Trapezregel aus der Entladeleistung (Watt) integriert
und in Kilowattstunden dargestellt.

Classes:
    BatteryTotalEnergyDischarge: Sensorentität zur Anzeige der aufsummierten Batterieentladeenergie.
"""

from homeassistant.core import HomeAssistant

from .total_integral_sensor import TotalIntegralSensor


class BatteryTotalEnergyDischarge(TotalIntegralSensor):
    """Sensorentität zur Anzeige der gesamten Batterieentladeenergie (kWh).

    Diese Entität summiert die Entladeleistung der Batterie über die Zeit auf, um
    die insgesamt abgegebene Energie zu berechnen. Sie nutzt dafür die Trapezregel
    zur Integration und stellt den Wert in Kilowattstunden dar.

    Attributes:
        _attr_entity_registry_enabled_default (bool): Gibt an, ob die Entität standardmäßig
           aktiviert ist.
        _entry (ConfigEntry): Die Konfigurationsdaten dieser Entität.
        _attr_icon (str): Das Symbol, das in der Benutzeroberfläche angezeigt wird.
        _attr_device_class (str): Gibt den Typ des Sensors an (hier: ENERGY).
        _attr_state_class (str): Gibt die Art des Sensorzustands an (TOTAL_INCREASING).
        _attr_native_unit_of_measurement (str): Die verwendete Energieeinheit (kWh).

    """

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Sensorentität für die Batterieentladeenergie.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag mit den Einstellungen dieser Entität.
            source_entity_id (str): Die Quell-Entity-ID, die die Entladeleistung in Watt liefert.

        """
        super().__init__(hass, entry, source_entity_id)
