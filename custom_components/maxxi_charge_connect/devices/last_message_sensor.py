"""Sensor-Entity zur Anzeige, wann die letzen Messdaten gekommen sind.

Die Klasse nutzt Home Assistants Dispatcher-System, um auf neue Sensordaten zu reagieren.
"""

import logging
from datetime import UTC, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    CONF_ENABLE_CLOUD_DATA,
    PROXY_STATUS_EVENTNAME,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class LastMessageSensor(SensorEntity):
    """SensorEntity für die aktuelle Uptime (uptime).

    Diese Entität zeigt umgerechnet in Tage, Stunden, Minuten und Sekunden an.
    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "LastMessageSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den LastMessageSensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_message_sensor"
        self._attr_icon = "mdi:update"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.DATE
        # self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Verbindet den Sensor mit dem Dispatcher-Signal zur Aktualisierung
        der Messwerte per Webhook.
        """

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def _handle_update(self, data):
        """Verarbeitet neue Webhook-Daten und aktualisiert den Sensorzustand.

        Und prüft auf Plausibilität.

        Args:
            data (dict): Die per Webhook empfangenen Sensordaten.

        """
        try:
            uptime_ms = int(data.get("uptime", 0))
            # _LOGGER.warning("Data: %s", data)

            now_utc = datetime.now(tz=UTC)

            # Startzeit berechnen
            # start_time_utc = now_utc - timedelta(milliseconds=uptime_ms)
            self._attr_native_value = now_utc

            seconds_total = uptime_ms / 1000

            # lesbares Format als extra attribute
            days, remainder = divmod(int(seconds_total), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            self._attr_extra_state_attributes = {
                "uptime": f"{days}d {hours}h {minutes}m {seconds}s",
                "raw_ms": uptime_ms,
                "data:": data,
            }
            self.async_write_ha_state()

        except ValueError as e:
            _LOGGER.warning("Uptime-Wert ungültig: %s", e)

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

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
