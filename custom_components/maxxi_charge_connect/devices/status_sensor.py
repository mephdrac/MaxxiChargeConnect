"""Sensor - der den aktuellen Zustand des Gerätes bzw. der Integration anzeigt."""

import logging
from homeassistant.const import EntityCategory, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from ..const import PROXY_ERROR_DEVICE_ID, WEBHOOK_SIGNAL_UPDATE, CONF_DEVICE_ID, CCU, ERROR, ERRORS, HTTP_SCAN_EVENTNAME, PROXY_STATUS_EVENTNAME, DOMAIN, WEBHOOK_SIGNAL_STATE  # noqa: TID252
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

    async def async_added_to_hass(self):
        """HA informiert uns, dass der Sensor hinzugefügt wurde."""
        await super().async_added_to_hass()

        # StatusSensor hört IMMER auf HTTP-Scan-Events
        self.hass.bus.async_listen(
            HTTP_SCAN_EVENTNAME, self.async_update_from_event
        )

        # Zusätzlich je nach Konfiguration auf Webhook/Cloud-Events hören
        if self._enable_cloud_data:
            # Cloud-Modus: Auf PROXY_STATUS_EVENTNAME hören
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            # Webhook-Modus: Auf WEBHOOK_SIGNAL_UPDATE hören (Dispatcher)
            entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
            update_signal = entry_data[WEBHOOK_SIGNAL_UPDATE]
            self._unsub_update = async_dispatcher_connect(
                self.hass, update_signal, self._wrapper_update
            )

        # Stale-Signal abonnieren
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        stale_signal = entry_data[WEBHOOK_SIGNAL_STATE]
        self._unsub_stale = async_dispatcher_connect(
            self.hass, stale_signal, self._wrapper_stale
        )

        # letzten Zustand wiederherstellen
        old_state = await self.async_get_last_state()
        if old_state is not None and old_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._attr_native_value = old_state.state

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

    async def async_update_from_event(self, event):
        """Empfängt sowohl Webhook- als auch HTTP-Scan-Events."""
        json_data = event.data.get("payload", {})

        # Bei HTTP-Scan Events deviceId prüfen, bei Webhook Events PROXY_ERROR_DEVICE_ID
        device_id_match = False
        if event.event_type == HTTP_SCAN_EVENTNAME:
            device_id_match = json_data.get("deviceId") == self._entry.data.get(CONF_DEVICE_ID)
        else:
            device_id_match = json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID)

        if device_id_match:
            await self.handle_update(json_data)

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
        self._state = "Off"
