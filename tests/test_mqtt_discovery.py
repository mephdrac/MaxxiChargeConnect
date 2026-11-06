"""Discovery ownership, persistence, templates and confirmed MQTT controls."""

import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.maxxi_charge_connect.connection.mqtt_discovery import MqttDiscovery, parse_discovery
from custom_components.maxxi_charge_connect.const import CONF_DEVICE_ID
from custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity import (
    DiscoveryBinarySensor,
    DiscoveryNumber,
    DiscoverySelect,
    DiscoverySensor,
    DiscoverySwitch,
    setup_discovery_entities,
)

MODULE = "custom_components.maxxi_charge_connect.connection.mqtt_discovery"
DEVICE = "CCU2-1020-BA5F-1F48"
CONFIG_TOPIC = f"homeassistant/number/{DEVICE}/maximum/config"
STATE_TOPIC = f"{DEVICE}/settings/state"
COMMAND_TOPIC = f"{DEVICE}/settings/set"


def description(**updates):
    config = {
        "name": "Maximum Output",
        "unique_id": f"{DEVICE}_maximum",
        "device": {"identifiers": [DEVICE], "sw_version": "2.43.0"},
        "state_topic": STATE_TOPIC,
        "command_topic": COMMAND_TOPIC,
        "value_template": "{{ value_json.maximum }}",
        "command_template": '{"maximum": {{ value }}}',
        "min": 0,
        "max": 2000,
        "step": 10,
    }
    config.update(updates)
    return json.dumps(config)


class DiscoveryParserTests(unittest.TestCase):
    def test_abbreviated_topics_and_exact_device_ownership(self):
        config = {
            "name": "Power",
            "uniq_id": "power",
            "dev": {"ids": DEVICE, "sw": "2.43.0"},
            "~": DEVICE,
            "stat_t": "~/power",
            "unit_of_meas": "W",
            "val_tpl": "{{ value_json.power }}",
        }
        specs = parse_discovery(f"homeassistant/sensor/{DEVICE}/power/config", json.dumps(config), DEVICE)
        self.assertEqual(specs[0].state_topic, f"{DEVICE}/power")
        self.assertEqual(specs[0].config["unit_of_measurement"], "W")
        self.assertFalse(parse_discovery(CONFIG_TOPIC, description(), DEVICE + "-other"))

    def test_other_device_and_cross_device_command_topics_are_rejected(self):
        self.assertFalse(parse_discovery(CONFIG_TOPIC, description(command_topic="another/command"), DEVICE))
        self.assertFalse(parse_discovery(CONFIG_TOPIC, description(state_topic=f"{DEVICE}/#"), DEVICE))
        self.assertFalse(
            parse_discovery(CONFIG_TOPIC, description(device={"identifiers": [DEVICE + "-extra"]}), DEVICE)
        )

    def test_vendor_prefix_is_supported_without_loosening_device_identity(self):
        specs = parse_discovery(
            CONFIG_TOPIC, description(state_topic=f"maxxi/{DEVICE}/state", command_topic=f"maxxi/{DEVICE}/set"), DEVICE
        )
        self.assertEqual(specs[0].state_topic, f"maxxi/{DEVICE}/state")

    def test_device_discovery_shared_metadata(self):
        config = {
            "dev": {"ids": [DEVICE], "sw": "2.44.0"},
            "~": DEVICE,
            "cmps": {
                "power": {"p": "sensor", "name": "Power", "stat_t": "~/power"},
                "mode": {
                    "p": "select",
                    "name": "Mode",
                    "stat_t": "~/mode",
                    "cmd_t": "~/mode/set",
                    "ops": ["auto", "off"],
                },
            },
        }
        specs = parse_discovery(f"homeassistant/device/{DEVICE}/config", json.dumps(config), DEVICE)
        self.assertEqual({spec.component for spec in specs}, {"sensor", "select"})

    def test_device_discovery_keeps_sensors_without_child_unique_ids_distinct(self):
        config = {
            "dev": {"ids": [DEVICE]},
            "unique_id": "device-level-id",
            "state_topic": STATE_TOPIC,
            "cmps": {"one": {"p": "sensor"}, "two": {"p": "sensor"}},
        }
        specs = parse_discovery(f"homeassistant/device/{DEVICE}/config", json.dumps(config), DEVICE)
        self.assertEqual(len({spec.key for spec in specs}), 2)

    def test_malformed_or_unsupported_descriptions_are_ignored(self):
        for payload in ("not json", "[]", "null", description(min="bad"), description(step=0), description(max=-1)):
            with self.subTest(payload=payload):
                self.assertFalse(parse_discovery(CONFIG_TOPIC, payload, DEVICE))
        self.assertFalse(parse_discovery("homeassistant/number/missing", description(), DEVICE))


class DiscoveryCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/maxxi-discovery-tests")
        self.entry = SimpleNamespace(entry_id="test", data={CONF_DEVICE_ID: DEVICE}, async_on_unload=MagicMock())
        storage_patch = patch(f"{MODULE}.Store")
        self.store = storage_patch.start().return_value
        self.store.async_load = AsyncMock(return_value=None)
        self.addCleanup(storage_patch.stop)
        self.subscribe = AsyncMock()
        self.publish = AsyncMock()
        self.coordinator = MqttDiscovery(self.hass, self.entry, self.subscribe, self.publish)
        await self.coordinator.async_load()
        await self.coordinator.async_start()

    async def asyncTearDown(self):
        self.coordinator.stop()

    async def add_number(self, **updates):
        await self.coordinator.async_receive(CONFIG_TOPIC, description(**updates))
        spec = next(iter(self.coordinator.specs.values()))
        await self.coordinator.async_receive(STATE_TOPIC, '{"maximum": 100}')
        return spec

    async def test_discovery_is_cached_and_state_topic_subscribed(self):
        spec = await self.add_number()
        self.subscribe.assert_any_await(STATE_TOPIC)
        self.assertEqual(self.coordinator.values[spec.key], "100")
        self.store.async_delay_save.assert_called_once()
        self.assertEqual(self.store.async_delay_save.call_args.args[0]()[CONFIG_TOPIC], description())
        self.assertTrue(self.coordinator.available(spec.key))

    async def test_cached_descriptions_restore_without_restoring_live_state(self):
        self.store.async_load.return_value = {CONFIG_TOPIC: description()}
        restored = MqttDiscovery(self.hass, self.entry, self.subscribe, self.publish)
        await restored.async_load()
        spec = next(iter(restored.specs.values()))
        self.assertFalse(restored.available(spec.key))
        self.assertFalse(restored.values)
        restored.stop()

    async def test_repeated_discovery_does_not_duplicate_entities(self):
        callback = MagicMock()
        self.coordinator.add_platform("number", callback)
        await self.add_number()
        before = callback.call_count
        await self.coordinator.async_receive(CONFIG_TOPIC, description())
        self.assertEqual(callback.call_count, before)
        self.assertEqual(len(self.coordinator.specs), 1)

    async def test_empty_discovery_withdraws_entity_and_cache(self):
        spec = await self.add_number()
        await self.coordinator.async_receive(CONFIG_TOPIC, b"")
        self.assertNotIn(spec.key, self.coordinator.specs)
        self.assertFalse(self.coordinator.available(spec.key))
        self.assertEqual(self.store.async_delay_save.call_args.args[0](), {})

    async def test_confirmation_arriving_during_publish_is_not_lost(self):
        spec = await self.add_number()

        async def reply(topic, payload):
            self.assertEqual(topic, COMMAND_TOPIC)
            self.assertEqual(json.loads(payload), {"maximum": 500.0})
            await self.coordinator.async_receive(STATE_TOPIC, '{"maximum": 500}')

        self.publish.side_effect = reply
        await self.coordinator.async_write(spec.key, 500.0, "500.0")
        self.assertFalse(self.coordinator._waiters)
        self.assertEqual(self.coordinator.values[spec.key], "500")

    async def test_wrong_acknowledgement_times_out_without_optimistic_state(self):
        spec = await self.add_number()

        async def reply(topic, payload):
            await self.coordinator.async_receive(STATE_TOPIC, '{"maximum": 300}')

        self.publish.side_effect = reply
        with patch(f"{MODULE}.COMMAND_TIMEOUT", 0.02):
            with self.assertRaisesRegex(HomeAssistantError, "did not confirm"):
                await self.coordinator.async_write(spec.key, 500, "500")
        self.assertEqual(self.coordinator.values[spec.key], "300")
        self.assertFalse(self.coordinator._waiters)

    async def test_unavailable_or_unsupported_firmware_prevents_writes(self):
        for version in ("2.42.9", "unknown"):
            await self.coordinator.async_receive(CONFIG_TOPIC, b"")
            spec = await self.add_number(device={"identifiers": [DEVICE], "sw_version": version})
            with self.assertRaisesRegex(HomeAssistantError, "firmware"):
                await self.coordinator.async_write(spec.key, 500, "500")
        self.publish.assert_not_awaited()
        await self.coordinator.async_receive(CONFIG_TOPIC, b"")
        spec = await self.add_number()
        self.coordinator.mark_stale()
        with self.assertRaisesRegex(HomeAssistantError, "not available"):
            await self.coordinator.async_write(spec.key, 500, "500")
        self.publish.assert_not_awaited()

    async def test_existing_value_does_not_publish(self):
        spec = await self.add_number()
        await self.coordinator.async_write(spec.key, 100.0, "100.0")
        self.publish.assert_not_awaited()

    async def test_publish_failure_is_reported_and_waiter_removed(self):
        spec = await self.add_number()
        self.publish.side_effect = OSError("disconnected")
        with self.assertRaisesRegex(HomeAssistantError, "could not be sent"):
            await self.coordinator.async_write(spec.key, 500, "500")
        self.assertFalse(self.coordinator._waiters)
        self.assertEqual(self.coordinator.values[spec.key], "100")

    async def test_command_echo_cannot_be_mistaken_for_confirmation(self):
        spec = await self.add_number(command_topic=STATE_TOPIC)
        with self.assertRaisesRegex(HomeAssistantError, "separate state topic"):
            await self.coordinator.async_write(spec.key, 500, "500")
        self.publish.assert_not_awaited()

    async def test_changed_description_unsubscribes_obsolete_topics(self):
        unsubscribe = MagicMock()
        self.coordinator._unsubscribe = unsubscribe
        await self.add_number()
        await self.coordinator.async_receive(CONFIG_TOPIC, description(state_topic=f"{DEVICE}/new_state"))
        unsubscribe.assert_called_once_with(STATE_TOPIC)
        self.subscribe.assert_any_await(f"{DEVICE}/new_state")

    async def test_offline_message_aborts_an_active_write(self):
        spec = await self.add_number(availability_topic=f"{DEVICE}/availability")
        await self.coordinator.async_receive(f"{DEVICE}/availability", "online")
        published = asyncio.Event()
        self.publish.side_effect = lambda *args: published.set()
        task = asyncio.create_task(self.coordinator.async_write(spec.key, 500, "500"))
        await asyncio.wait_for(published.wait(), 1)
        await self.coordinator.async_receive(f"{DEVICE}/availability", "offline")
        with self.assertRaisesRegex(HomeAssistantError, "offline"):
            await task

    async def test_firmware_sensor_can_supply_the_version(self):
        spec = await self.add_number(device={"identifiers": [DEVICE]})
        config = description(
            name="CCU ver",
            state_topic=f"{DEVICE}/version",
            value_template=None,
            device={"identifiers": [DEVICE]},
        )
        await self.coordinator.async_receive(f"homeassistant/sensor/{DEVICE}/version/config", config)
        await self.coordinator.async_receive(f"{DEVICE}/version", "2.43.1")
        self.assertEqual(self.coordinator._firmware(spec), (2, 43, 1))

    async def test_unload_aborts_pending_command(self):
        spec = await self.add_number()
        published = asyncio.Event()
        self.publish.side_effect = lambda *args: published.set()
        command = asyncio.create_task(self.coordinator.async_write(spec.key, 500, "500"))
        await asyncio.wait_for(published.wait(), 1)
        self.coordinator.stop()
        with self.assertRaisesRegex(HomeAssistantError, "stopped responding"):
            await command

    async def test_concurrent_writes_to_one_setting_are_serialized(self):
        spec = await self.add_number()
        first_sent = asyncio.Event()
        second_sent = asyncio.Event()

        async def published(topic, payload):
            value = json.loads(payload)["maximum"]
            (first_sent if value == 500 else second_sent).set()

        self.publish.side_effect = published
        first = asyncio.create_task(self.coordinator.async_write(spec.key, 500, "500"))
        await asyncio.wait_for(first_sent.wait(), 1)
        second = asyncio.create_task(self.coordinator.async_write(spec.key, 600, "600"))
        try:
            self.assertFalse(second_sent.is_set())
            await self.coordinator.async_receive(STATE_TOPIC, '{"maximum": 500}')
            await asyncio.wait_for(first, 1)
            await asyncio.wait_for(second_sent.wait(), 1)
            await self.coordinator.async_receive(STATE_TOPIC, '{"maximum": 600}')
            await asyncio.wait_for(second, 1)
            self.assertEqual(self.coordinator.values[spec.key], "600")
        finally:
            for task in (first, second):
                if not task.done():
                    task.cancel()
            await asyncio.gather(first, second, return_exceptions=True)

    async def test_number_range_and_step_are_enforced(self):
        spec = await self.add_number()
        entity = DiscoveryNumber(self.coordinator, spec)
        for value in (-10, 2001, 11, float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(HomeAssistantError):
                    await entity.async_set_native_value(value)
        self.publish.assert_not_awaited()
        self.assertEqual(entity.native_value, 100)

    async def test_availability_and_invalid_templates(self):
        spec = await self.add_number(availability_topic=f"{DEVICE}/availability")
        self.assertFalse(self.coordinator.available(spec.key))
        await self.coordinator.async_receive(f"{DEVICE}/availability", b"online")
        self.assertTrue(self.coordinator.available(spec.key))
        await self.coordinator.async_receive(f"{DEVICE}/availability", b"offline")
        self.assertFalse(self.coordinator.available(spec.key))
        self.assertFalse(await self.coordinator.async_receive(STATE_TOPIC, "not-json"))

    async def test_platform_adds_once_and_preserves_identity_on_name_change(self):
        self.hass.data["maxxi_charge_connect"] = {"test": {"mqtt_discovery": self.coordinator}}
        add_entities = MagicMock()
        setup_discovery_entities(self.hass, self.entry, add_entities, "number")
        spec = await self.add_number()
        entity = add_entities.call_args.args[0][0]
        identity = entity.unique_id
        await self.coordinator.async_receive(CONFIG_TOPIC, description(name="Renamed output"))
        self.assertEqual(entity.unique_id, identity)
        self.assertEqual(entity.name, "Renamed output")
        add_entities.assert_called_once()

    async def test_select_and_switch_use_declared_payloads_and_confirmations(self):
        for component, config in (
            ("select", {"options": ["auto", "off"]}),
            (
                "switch",
                {"payload_on": "enable", "payload_off": "disable", "state_on": "enabled", "state_off": "disabled"},
            ),
        ):
            topic = f"homeassistant/{component}/{DEVICE}/setting/config"
            await self.coordinator.async_receive(
                topic, description(value_template=None, command_template=None, **config)
            )
        specs = {spec.component: spec for spec in self.coordinator.specs.values()}
        await self.coordinator.async_receive(STATE_TOPIC, "off")
        select = DiscoverySelect(self.coordinator, specs["select"])
        with self.assertRaises(HomeAssistantError):
            await select.async_select_option("invalid")

        async def reply(topic, payload):
            await self.coordinator.async_receive(STATE_TOPIC, "enabled" if payload == "enable" else payload)

        self.publish.side_effect = reply
        await select.async_select_option("auto")
        self.assertEqual(select.current_option, "auto")
        switch = DiscoverySwitch(self.coordinator, specs["switch"])
        await self.coordinator.async_receive(STATE_TOPIC, "disabled")
        await switch.async_turn_on()
        self.assertTrue(switch.is_on)

    async def test_nested_availability_template_and_binary_sensor(self):
        config = description(
            name="Fault",
            value_template=None,
            payload_on="fault",
            payload_off="ok",
            availability=[{"topic": f"{DEVICE}/status", "value_template": "{{ value_json.status }}"}],
        )
        await self.coordinator.async_receive(f"homeassistant/binary_sensor/{DEVICE}/fault/config", config)
        spec = next(iter(self.coordinator.specs.values()))
        entity = DiscoveryBinarySensor(self.coordinator, spec)
        await self.coordinator.async_receive(STATE_TOPIC, "fault")
        self.assertTrue(entity.is_on)
        self.assertFalse(entity.available)
        await self.coordinator.async_receive(f"{DEVICE}/status", '{"status": "online"}')
        self.assertTrue(entity.available)
        self.assertFalse(await self.coordinator.async_receive(STATE_TOPIC, "invalid"))
        self.assertTrue(entity.is_on)
        await self.coordinator.async_receive(STATE_TOPIC, "ok")
        self.assertFalse(entity.is_on)

    async def test_text_and_numeric_discovery_sensors(self):
        for component_id, updates in (
            ("text", {"value_template": None, "name": "Firmware"}),
            ("numeric", {"value_template": None, "unit_of_measurement": "W", "state_class": "measurement"}),
        ):
            topic = f"homeassistant/sensor/{DEVICE}/{component_id}/config"
            await self.coordinator.async_receive(topic, description(**updates))
        await self.coordinator.async_receive(STATE_TOPIC, "125")
        entities = [DiscoverySensor(self.coordinator, spec) for spec in self.coordinator.specs.values()]
        self.assertEqual([entity.native_value for entity in entities], ["125", 125.0])
