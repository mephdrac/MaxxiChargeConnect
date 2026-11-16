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
    MQTT_DISCOVERY_COORDINATOR,
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
        self.async_on_remove(self._subscribe_updates(entry_data))
        # Covers messages that arrived before the entities were added.
        self._read_stats()

    def _subscribe_updates(self, entry_data):
        return async_dispatcher_connect(self.hass, entry_data[MQTT_DIAGNOSTICS_SIGNAL], self._receive_update)

    def _read_stats(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        self._stats = dict(entry_data[MQTT_RECEIVE_STATS])
        discovery = entry_data.get(MQTT_DISCOVERY_COORDINATOR)
        self._stats["discovered_entities"] = len(discovery.specs) if discovery else 0
        if self._stats_key == "sensor_coverage":
            self._stats["sensor_coverage"] = discovery.sensor_mapping_report()["coverage"] if discovery else 0
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
            "discovered_entities": self._stats.get("discovered_entities", 0),
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


class MqttDiscoveredEntitiesSensor(_MqttDiagnosticsSensor):
    """Show the current discovery count, including configurations mapped to old sensors."""

    _attr_translation_key = "mqtt_discovered_entities"
    _attr_icon = "mdi:magnify-scan"
    _attr_native_value = 0
    _stats_key = "discovered_entities"

    def _subscribe_updates(self, entry_data):
        discovery = entry_data.get(MQTT_DISCOVERY_COORDINATOR)
        if discovery is not None:
            return discovery.add_listener(self._receive_update)
        return super()._subscribe_updates(entry_data)

    @property
    def extra_state_attributes(self):
        return {"broker": "internal" if self._entry.data.get(CONF_ENABLE_MQTT_BROKER, False) else "external"}


class MqttSensorCoverageSensor(_MqttDiagnosticsSensor):
    """Visible, complete source audit for all sensors from our own CCU factories."""

    _attr_translation_key = "mqtt_sensor_coverage"
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_native_value = 0
    _attr_native_unit_of_measurement = "%"
    _stats_key = "sensor_coverage"

    def _subscribe_updates(self, entry_data):
        coordinator = entry_data.get(MQTT_DISCOVERY_COORDINATOR)
        if coordinator is not None:
            return coordinator.add_mapping_listener(self._receive_update)
        return super()._subscribe_updates(entry_data)

    @property
    def extra_state_attributes(self):
        coordinator = self.hass.data[DOMAIN][self._entry.entry_id].get(MQTT_DISCOVERY_COORDINATOR)
        if coordinator is None:
            return {"missing": [], "sensors": {}, "unmapped_discovery": []}
        report = coordinator.sensor_mapping_report()
        return {key: report[key] for key in ("missing", "sensors", "unmapped_discovery")}
