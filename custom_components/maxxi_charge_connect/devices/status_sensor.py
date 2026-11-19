"""Sensor - der den aktuellen Zustand des Gerätes bzw. der Integration anzeigt."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory

# pylint: disable=line-too-long
from ..const import (
    CCU,
    CONF_DEVICE_ID,
    DOMAIN,
    ERROR,
    ERRORS,
    HTTP_SCAN_EVENTNAME,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)
_OFFLINE = "Offline"


class StatusSensor(BaseWebhookSensor):
    """Sensor für MaxxiCloud-Daten vom Proxy."""

    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_status_sensor"

        self._attr_native_value = _OFFLINE
        self._attr_available = True
        self._attr_device_class = None
        self._attr_icon = "mdi:alert-circle"

        self._attr_extra_state_attributes = {}
        self._http_scan_coordinator = None

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        """HA informiert uns, dass der Sensor hinzugefügt wurde."""
        await super().async_added_to_hass()

        self._http_scan_coordinator = self.hass.data[DOMAIN][self._entry.entry_id]["coordinator"]
        self.async_on_remove(self._http_scan_coordinator.async_add_listener(self.async_write_ha_state))

    def format_uptime(self, seconds: int):
        """Berechnet die Update aus einem integer."""

        days, remainder = divmod(seconds, 86400)  # 86400 Sekunden pro Tag
        hours, remainder = divmod(remainder, 3600)  # 3600 Sekunden pro Stunde
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @property
    def extra_state_attributes(self):
        """Show the result of the last HTTP scan alongside the telemetry state."""
        attributes = self._attr_extra_state_attributes
        if self._http_scan_coordinator is None:
            return attributes
        return {
            **attributes,
            "http_scan_target": self._http_scan_coordinator.scan_target,
            "http_scan_result": self._http_scan_coordinator.scan_result,
        }

    async def async_update_from_event(self, event):
        """Empfängt Statusdaten aus dem lokalen Proxy."""
        if event.event_type == HTTP_SCAN_EVENTNAME:
            return

        json_data = event.data.get("payload", {})

        device_id = json_data.get(PROXY_ERROR_DEVICE_ID)
        if device_id == ERRORS:
            device_id = json_data.get(CCU)
        if device_id and device_id == self._entry.data.get(CONF_DEVICE_ID):
            await self.handle_update(json_data)
            self.async_write_ha_state()

    async def handle_update(self, data):
        """Wird aufgerufen, beim Empfang neuer Daten vom Dispatcher."""

        _LOGGER.debug("Status - Event erhalten: %s", data)

        if data.get(CCU) == self._entry.data.get(CONF_DEVICE_ID) and data.get(PROXY_ERROR_DEVICE_ID) == ERRORS:
            _LOGGER.warning("Status - Error - Event erhalten: %s", data)

            self._attr_native_value = f"Fehler ({data.get(ERROR, 'Unbekannt')})"
            self._attr_extra_state_attributes = data

        elif data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            _LOGGER.info("Status - OK - Event erhalten: %s", data)
            self._attr_native_value = data.get("integration_state", "OK")
            self._attr_extra_state_attributes = data

    async def handle_stale(self):
        """Zeige nach Ablauf des Empfangstimeouts Offline an."""
        self._attr_native_value = _OFFLINE
        self._attr_extra_state_attributes = {}
