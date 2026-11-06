"""Receive diagnostics for each CCU V2, independent of telemetry availability."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    CONF_ENABLE_MQTT_BROKER,
    DOMAIN,
    MQTT_DIAGNOSTICS_SIGNAL,
    MQTT_RECEIVE_STATS,
)


class _MqttDiagnosticsSensor(SensorEntity):
    """Keep reception history visible even when the CCU stops sending."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = True
    _stats_key: str

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_translation_key}"
        self._stats = {}
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        self.async_on_remove(
            async_dispatcher_connect(self.hass, entry_data[MQTT_DIAGNOSTICS_SIGNAL], self._receive_update)
        )
        # Covers messages that arrived before the entities were added.
        self._read_stats()

    def _read_stats(self) -> None:
        self._stats = dict(self.hass.data[DOMAIN][self._entry.entry_id][MQTT_RECEIVE_STATS])
        self._attr_native_value = self._stats[self._stats_key]

    @callback
    def _receive_update(self) -> None:
        self._read_stats()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Show the last accepted topic, counter start and broker selection."""
        started_at = self._stats.get("started_at")
        return {
            "last_topic": self._stats.get("last_topic"),
            "counting_since": started_at.isoformat() if started_at else None,
            "broker": "internal" if self._entry.data.get(CONF_ENABLE_MQTT_BROKER, False) else "external",
        }


class MqttLastReceivedSensor(_MqttDiagnosticsSensor):
    """UTC timestamp of the most recent successfully parsed telemetry message."""

    _attr_translation_key = "mqtt_last_received"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:message-clock-outline"
    _attr_native_value = None
    _stats_key = "last_received"


class MqttReceivedCountSensor(_MqttDiagnosticsSensor):
    """Count accepted telemetry messages since this entry was loaded."""

    _attr_translation_key = "mqtt_received_count"
    _attr_icon = "mdi:counter"
    _attr_native_value = 0
    _stats_key = "received_count"
