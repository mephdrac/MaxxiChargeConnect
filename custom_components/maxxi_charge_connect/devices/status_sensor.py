"""Sensor - der den aktuellen Zustand des Gerätes bzw. der Integration anzeigt."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from ..const import (
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    DEVICE_INFO,
    PROXY_ERROR_DEVICE_ID,
    CONF_DEVICE_ID,
    CCU,
    ERROR,
    ERRORS,
    CONF_ENABLE_CLOUD_DATA
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class StatusSensor(SensorEntity):
    """Sensor für MaxxiCloud-Daten vom Proxy."""

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "StatusSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status_sensor"

        self._unsub_dispatcher = None
        self._state = str(None)
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_icon = "mdi:alert-circle"

        self._attr_extra_state_attributes = {}

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Register.

        Registriert den Sensor für Updates über das Dispatcher-Signal
        bei Hinzufügen zur Home Assistant Instanz.
        """

        # if self._enable_cloud_data:
        _LOGGER.info("Daten kommen vom Proxy")
        self.hass.bus.async_listen(
            PROXY_STATUS_EVENTNAME, self.async_update_from_event
        )
        # else:
        _LOGGER.info("Daten kommen vom Webhook")
        signal_sensor = (
            f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
        )

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )
        self.async_on_remove(self._unsub_dispatcher)

    async def async_will_remove_from_hass(self):
        """Wird aufgerufen, wenn die Entity aus Home Assistant entfernt wird.

        Hebt die Registrierung beim Dispatcher auf, um Speicherlecks zu vermeiden.
        """
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    def format_uptime(self, seconds: int):
        """Berechnet die Update aus einem integer."""

        days, remainder = divmod(seconds, 86400)  # 86400 Sekunden pro Tag
        hours, remainder = divmod(remainder, 3600)  # 3600 Sekunden pro Stunde
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @property
    def native_value(self):
        """Statuswert des Feldes."""

        return self._state

    @property
    def extra_state_attributes(self):
        """Weitere Attribute die visualisiert werden."""

        return self._attr_extra_state_attributes

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        # if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
        await self._handle_update(json_data)

    async def _handle_update(self, data):
        """Wird aufgerufen, beim Empfang neuer Daten vom Dispatcher."""

        _LOGGER.debug("Status - Event erhalten: %s", data)

        if (
            data.get(CCU) == self._entry.data.get(CONF_DEVICE_ID)
            and data.get(PROXY_ERROR_DEVICE_ID) == ERRORS
        ):
            _LOGGER.warning("Status - Error - Event erhalten: %s", data)

            self._state = f"Fehler ({data.get(ERROR, "Unbekannt")})"
            self._attr_extra_state_attributes = data
            self.async_write_ha_state()

        elif data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(
            CONF_DEVICE_ID
        ):
            _LOGGER.info("Status - OK - Event erhalten: %s", data)
            self._state = data.get("integration_state", "OK")
            self._attr_extra_state_attributes = data
            self.async_write_ha_state()

        # self._state = "TEST"

        # if self._key == PROXY_ERROR_DEVICE_ID:
        #     self._state = data.get(PROXY_ERROR_DEVICE_ID)
        # elif self._key == "ccu":
        #     self._state = data.get("ccu")
        # elif self._key == "uptime":
        #     uptime_seconds = int(json_data.get("uptime"))
        #     self._state = self.format_uptime(uptime_seconds)

        # elif self._key == "ip":
        #     self._state = data.get("ip")
        # elif self._key == "error_code":
        #     self._state = data.get("error_code")
        # elif self._key == "error_message":
        #     self._state = data.get("error_message")
        # elif self._key == "total_errors":
        #     self._state = data.get("total_errors")
        # elif self._key == "last_payload":
        #     self._state = str(data.get("payload", {}))[:100]
        # elif self._key == "forwarding":
        #     self._state = "enabled" if data.get("forwarded") else "disabled"

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
