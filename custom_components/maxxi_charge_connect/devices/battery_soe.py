"""Dieses Modul definiert die Sensor-Entity `BatterySoE`.

Die Entity stellt den aktuellen „State of Energy“ (SoE) des Batteriesystems
dar und aktualisiert ihren Zustand dynamisch anhand von empfangenen Sensordaten.

Die Klasse `BatterySoE` erbt von `SensorEntity` und implementiert alle nötigen Methoden für die
Integration in Home Assistant, inklusive Registrierung von Updates über Dispatcher-Signale
und Geräteinformationen.

Konstanten:
    - DOMAIN: Die Domain der Integration, z.B. "maxxi_charge_connect".

"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatterySoE(BaseWebhookSensor):
    """SensorEntity zur Darstellung des Batteriezustands in Wattstunden (State of Energy).

    Attribute:
        _attr_suggested_display_precision (int): Vorgeschlagene Genauigkeit für Anzeige.
        _entry (ConfigEntry): Referenz auf den ConfigEntry dieser Instanz.
        _attr_unique_id (str): Eindeutige ID der Entity.
        _attr_icon (str): Icon für die Entity im Frontend.
        _attr_native_value (float|None): Aktueller State of Energy-Wert.
        _attr_device_class (None): Keine spezielle Device Class zugewiesen.
        _attr_native_unit_of_measurement (str): Einheit der Messgröße (Wh).

    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatterySoE"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die BatterySoE Sensor-Entity mit den Grundeinstellungen.

        Args:
            entry (ConfigEntry): Konfigurationseintrag mit den Nutzereinstellungen.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_soe"
        self._attr_icon = "mdi:home-battery"
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    async def handle_update(self, data):
        """Aktualisiert den State of Energy anhand der empfangenen Sensordaten.

        Args:
            data (dict): Aktuelle Sensordaten mit Batteriesystem-Informationen.

        """
        batteries_info = data.get("batteriesInfo")
        if (
            batteries_info
            and isinstance(batteries_info, list)
            and len(batteries_info) > 0
        ):
            batteries_info = data.get("batteriesInfo", [])
            total_capacity = sum(
                battery.get("batteryCapacity", 0) for battery in batteries_info
            )

            self._attr_native_value = total_capacity
            self.async_write_ha_state()
