"""Sensor - der den aktuellen Zustand des Gerätes bzw. der Integration anzeigt."""

import logging
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from ..const import PROXY_ERROR_DEVICE_ID, CONF_DEVICE_ID, CCU, ERROR, ERRORS  # noqa: TID252
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class StatusSensor(BaseWebhookSensor):
    """Sensor für MaxxiCloud-Daten vom Proxy."""

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "StatusSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_status_sensor"

        self._unsub_dispatcher = None
        self._state = str(None)
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_icon = "mdi:alert-circle"

        self._attr_extra_state_attributes = {}

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def format_uptime(self, seconds: int):
        """Berechnet die Update aus einem integer."""

        days, remainder = divmod(seconds, 86400)  # 86400 Sekunden pro Tag
        hours, remainder = divmod(remainder, 3600)  # 3600 Sekunden pro Stunde
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @property
    def extra_state_attributes(self):
        """Weitere Attribute die visualisiert werden."""

        return self._attr_extra_state_attributes

    async def handle_update(self, data):
        """Wird aufgerufen, beim Empfang neuer Daten vom Dispatcher."""

        _LOGGER.debug("Status - Event erhalten: %s", data)

        if (
            data.get(CCU) == self._entry.data.get(CONF_DEVICE_ID)
            and data.get(PROXY_ERROR_DEVICE_ID) == ERRORS
        ):
            _LOGGER.warning("Status - Error - Event erhalten: %s", data)

            self._state = f"Fehler ({data.get(ERROR, 'Unbekannt')})"
            self._attr_native_value = self._state
            self._attr_extra_state_attributes = data

        elif data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            _LOGGER.info("Status - OK - Event erhalten: %s", data)
            self._state = data.get("integration_state", "OK")
            self._attr_native_value = self._state
            self._attr_extra_state_attributes = data

    async def handle_stale(self):
        """Bei stale verfügbar bleiben und letzten Status beibehalten."""
        self._attr_available = True
