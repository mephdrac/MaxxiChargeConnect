"""Reception counters remain useful before first telemetry and after a timeout."""

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory

from custom_components.maxxi_charge_connect.const import (
    CONF_ENABLE_MQTT_BROKER,
    DOMAIN,
    MQTT_DIAGNOSTICS_SIGNAL,
    MQTT_RECEIVE_STATS,
)
from custom_components.maxxi_charge_connect.devices.mqtt_diagnostics import (
    MqttLastReceivedSensor,
    MqttReceivedCountSensor,
)


class MqttDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.entry = SimpleNamespace(entry_id="one", data={CONF_ENABLE_MQTT_BROKER: True})
        self.started_at = datetime(2026, 11, 6, 15, tzinfo=UTC)
        self.stats = {
            "received_count": 0,
            "last_received": None,
            "last_topic": None,
            "started_at": self.started_at,
        }
        self.hass = MagicMock()
        self.hass.data = {
            DOMAIN: {
                "one": {
                    MQTT_RECEIVE_STATS: self.stats,
                    MQTT_DIAGNOSTICS_SIGNAL: "diagnostics_one",
                }
            }
        }
        self.sensors = [MqttLastReceivedSensor(self.entry), MqttReceivedCountSensor(self.entry)]
        self.unsubscribe = MagicMock()
        for sensor in self.sensors:
            sensor.hass = self.hass
            sensor.async_write_ha_state = MagicMock()
            sensor.async_on_remove = MagicMock()
            with patch(
                "custom_components.maxxi_charge_connect.devices.mqtt_diagnostics.async_dispatcher_connect",
                return_value=self.unsubscribe,
            ) as connect:
                await sensor.async_added_to_hass()
                connect.assert_called_once_with(self.hass, "diagnostics_one", sensor._receive_update)

    async def test_initial_diagnostics_are_enabled_and_linked_to_ccu(self):
        last_received, count = self.sensors
        self.assertIsNone(last_received.native_value)
        self.assertEqual(count.native_value, 0)
        self.assertEqual(last_received.device_class, SensorDeviceClass.TIMESTAMP)
        for sensor in self.sensors:
            self.assertTrue(sensor.available)
            self.assertTrue(sensor.entity_registry_enabled_default)
            self.assertEqual(sensor.entity_category, EntityCategory.DIAGNOSTIC)
            self.assertEqual(sensor.device_info["identifiers"], {(DOMAIN, "one")})
            sensor.async_on_remove.assert_called_once_with(self.unsubscribe)
            self.assertEqual(sensor.extra_state_attributes["broker"], "internal")

    async def test_updates_expose_timestamp_count_topic_and_counter_start(self):
        timestamp = datetime(2026, 11, 6, 15, 1, tzinfo=UTC)
        self.stats.update(
            {"received_count": 2, "last_received": timestamp, "last_topic": "Maxxi-one/battery/telemetry"}
        )
        for sensor in self.sensors:
            sensor._receive_update()
            sensor.async_write_ha_state.assert_called_once()
            self.assertEqual(sensor.extra_state_attributes["last_topic"], "Maxxi-one/battery/telemetry")
            self.assertEqual(sensor.extra_state_attributes["counting_since"], self.started_at.isoformat())
        self.assertEqual(self.sensors[0].native_value, timestamp)
        self.assertEqual(self.sensors[1].native_value, 2)

    async def test_messages_before_entity_setup_are_not_lost(self):
        self.stats["received_count"] = 7
        sensor = MqttReceivedCountSensor(self.entry)
        sensor.hass = self.hass
        with patch("custom_components.maxxi_charge_connect.devices.mqtt_diagnostics.async_dispatcher_connect"):
            await sensor.async_added_to_hass()
        self.assertEqual(sensor.native_value, 7)

    async def test_external_broker_attribute(self):
        self.entry.data[CONF_ENABLE_MQTT_BROKER] = False
        self.assertEqual(self.sensors[0].extra_state_attributes["broker"], "external")
