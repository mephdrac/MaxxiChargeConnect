"""Sensor für die gesamte Batterieladeenergie (BatteryTotalEnergyCharge).

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte in die Batterie eingespeiste Energie über die Zeit aufsummiert.

Die Energiemenge wird mithilfe der Trapezregel integriert, auf Kilo­watt­stunden normiert und
täglich aktualisiert.

Classes:
    BatteryTotalEnergyCharge: Sensorentität zur Anzeige der aufsummierten Batterieladeenergie.
"""

from .total_integral_sensor import TotalIntegralSensor
from .base_webhook_sensor import BaseWebhookSensor
from homeassistant.config_entries import ConfigEntry

from ..tools import (
    get_entity
)


class BatteryTotalEnergyChargeSensor(BaseWebhookSensor, TotalIntegralSensor):
    """Sensorentität zur Anzeige der gesamten Batterieladeenergie (kWh).

    Diese Entität summiert die Batterieladeleistung (Watt) über die Zeit auf, um
    die insgesamt eingespeiste Energie zu berechnen. Sie nutzt dafür die Trapezregel
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
    def __init__(self, entry: ConfigEntry, index: int) -> None:
        super().__init__(self.hass, entry, get_entity(self.hass, "maxxi_charge_connect", f"{entry.entry_id}_battery_charge_sensor_{index}").entity_id)


