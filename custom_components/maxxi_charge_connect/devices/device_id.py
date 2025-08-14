"""TextEntity zur Anzeige der Geräte-ID eines Batteriesystems in Home Assistant.

Diese Entität zeigt die eindeutige Geräte-ID (z. B. Seriennummer) an, die per Webhook
übermittelt wird. Sie dient primär Diagnosezwecken und ist in der Kategorie
'diagnostic' einsortiert.
"""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_ERROR_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class DeviceId(SensorEntity):
    """TextEntity für die Anzeige der Geräte-ID eines verbundenen Geräts."""

    _attr_translation_key = "device_id"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Entity zur Anzeige der Geräte-ID.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        self._entry = entry
        # self._attr_name = "Device ID"
        self._attr_unique_id = f"{entry.entry_id}_deviceid"
        self._attr_icon = "mdi:identifier"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Verbindet sich mit dem Dispatcher-Signal, um auf eingehende Webhook-Daten zu reagieren.
        """
        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_ERROR_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")

            signal_sensor = (
                f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
            )

            self.async_on_remove(
                async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
            )

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

    async def _handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert die Geräte-ID.

        Args:
            data (dict): Die per Webhook empfangenen Daten.

        """

        self._attr_native_value = data.get("deviceId")
        self.async_write_ha_state()

    def set_value(self, value):
        """SetValue."""
        self._attr_native_value = value

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
