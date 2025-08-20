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
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatterySoE(SensorEntity):
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
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Battery State of Energy"
        self._attr_unique_id = f"{entry.entry_id}_battery_soe"
        self._attr_icon = "mdi:home-battery"
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Register.

        Registriert den Sensor für Updates über das Dispatcher-Signal
        bei Hinzufügen zur Home Assistant Instanz.
        """

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")

            signal_sensor = (
                f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
            )

            remove_callback = async_dispatcher_connect(
                self.hass, signal_sensor, self._handle_update
            )
            self.async_on_remove(remove_callback)

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

    async def _handle_update(self, data):
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

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
