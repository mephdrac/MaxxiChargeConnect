"""Broker selection, CCU routing and Home Assistant lifecycle regression tests."""

import asyncio
import json
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import voluptuous as vol
from amqtt.client import MQTTClient
from homeassistant.const import CONF_NAME, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.maxxi_charge_connect import async_migrate_entry, async_unload_entry
from custom_components.maxxi_charge_connect.config_flow import MaxxiChargeConnectConfigFlow
from custom_components.maxxi_charge_connect.connection.ccu_v2_connection import ccuV2Connection
from custom_components.maxxi_charge_connect.const import (
    CCU_V1,
    CCU_V2,
    CONF_CCU_VERSION,
    CONF_DEVICE_ID,
    CONF_ENABLE_MQTT_BROKER,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    DOMAIN,
    MQTT_BROKER_MANAGER,
    MQTT_RECEIVE_STATS,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
)
from custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity import DiscoveryNumber
from custom_components.maxxi_charge_connect.devices.pv_power import PvPower

CONNECTION_MODULE = "custom_components.maxxi_charge_connect.connection.ccu_v2_connection"


def make_hass():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    hass.async_create_background_task.side_effect = lambda coroutine, name: asyncio.create_task(coroutine)
    return hass


def make_entry(entry_id="one", internal=False, port=1883):
    return SimpleNamespace(
        entry_id=entry_id,
        data={
            CONF_CCU_VERSION: CCU_V2,
            CONF_DEVICE_ID: f"Maxxi-{entry_id}",
            CONF_ENABLE_MQTT_BROKER: internal,
            CONF_MQTT_PORT: port,
            CONF_MQTT_USERNAME: "ccu",
            CONF_MQTT_PASSWORD: "secret",
        },
    )


class MqttFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = MaxxiChargeConnectConfigFlow()
        self.flow.async_set_unique_id = AsyncMock()
        self.flow._abort_if_unique_id_configured = MagicMock()
        self.flow.hass = make_hass()
        self.flow._ccu_version = CCU_V2
        self.flow._name = "CCU"
        self.flow._device_id = "Maxxi-one"
        self.flow._async_current_entries = MagicMock(return_value=[])
        self.flow.async_show_form = MagicMock(side_effect=lambda **kwargs: kwargs)
        self.flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: kwargs)

    async def test_external_default_creates_entry_without_credentials(self):
        result = await self.flow.async_step_v2({CONF_NAME: "CCU", CONF_DEVICE_ID: "Maxxi-one"})
        self.assertFalse(result["data"][CONF_ENABLE_MQTT_BROKER])
        self.assertNotIn(CONF_MQTT_PASSWORD, result["data"])

    async def test_internal_requires_password_and_valid_port(self):
        self.flow._enable_mqtt_broker = True
        result = await self.flow.async_step_mqtt({CONF_MQTT_PORT: 1883, CONF_MQTT_USERNAME: "ccu"})
        self.assertEqual(result["errors"][CONF_MQTT_PASSWORD], "required")
        with self.assertRaises(vol.Invalid):
            result["data_schema"]({CONF_MQTT_PORT: 0, CONF_MQTT_USERNAME: "ccu"})
        result = await self.flow.async_step_mqtt(
            {CONF_MQTT_PORT: 1884, CONF_MQTT_USERNAME: "ccu", CONF_MQTT_PASSWORD: "secret"}
        )
        self.assertEqual(result["data"][CONF_MQTT_PORT], 1884)

    async def test_second_ccu_inherits_password_and_rejects_conflicts(self):
        self.flow._enable_mqtt_broker = True
        self.flow._async_current_entries.return_value = [make_entry(internal=True)]
        result = await self.flow.async_step_mqtt({CONF_MQTT_PORT: 1884, CONF_MQTT_USERNAME: "ccu"})
        self.assertEqual(result["errors"]["base"], "mqtt_settings_conflict")
        result = await self.flow.async_step_mqtt({CONF_MQTT_PORT: 1883, CONF_MQTT_USERNAME: "ccu"})
        self.assertEqual(result["data"][CONF_MQTT_PASSWORD], "secret")

    async def test_reconfigure_blank_password_preserves_secret(self):
        entry = make_entry(internal=True)
        entry.data[CONF_NAME] = "CCU"
        self.flow._get_reconfigure_entry = MagicMock(return_value=entry)
        self.flow._async_current_entries.return_value = [entry]
        self.flow.async_update_reload_and_abort = MagicMock(side_effect=lambda entry, **kwargs: kwargs)
        result = await self.flow.async_step_reconfigure()
        self.assertEqual(result["step_id"], "v2")
        await self.flow.async_step_v2({CONF_NAME: "CCU", CONF_DEVICE_ID: "Maxxi-one", CONF_ENABLE_MQTT_BROKER: True})
        result = await self.flow.async_step_mqtt({CONF_MQTT_PORT: 1883, CONF_MQTT_USERNAME: "ccu"})
        self.assertEqual(result["data_updates"][CONF_MQTT_PASSWORD], "secret")

    async def test_duplicate_and_wildcard_device_ids_rejected(self):
        self.flow._async_current_entries.return_value = [make_entry()]
        result = await self.flow.async_step_v2({CONF_NAME: "CCU", CONF_DEVICE_ID: "Maxxi-one"})
        self.assertEqual(result["errors"][CONF_DEVICE_ID], "device_exists")
        result = await self.flow.async_step_v2({CONF_NAME: "CCU", CONF_DEVICE_ID: "Maxxi-+"})
        self.assertEqual(result["errors"][CONF_DEVICE_ID], "invalid_device_id")


class MqttConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = make_hass()
        self.connections = []
        storage_patch = patch("custom_components.maxxi_charge_connect.connection.mqtt_discovery.Store")
        store = storage_patch.start().return_value
        store.async_load = AsyncMock(return_value=None)
        self.addCleanup(storage_patch.stop)

    async def asyncTearDown(self):
        for connection in self.connections:
            await connection.async_unload()
        manager = self.hass.data.get(DOMAIN, {}).get(MQTT_BROKER_MANAGER)
        if manager:
            await manager.async_shutdown()

    def connection(self, entry):
        connection = ccuV2Connection(self.hass, entry)
        self.connections.append(connection)
        return connection

    async def test_real_internal_broker_routes_two_ccus_to_existing_parsers(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        one = self.connection(make_entry("one", True, port))
        two = self.connection(make_entry("two", True, port))
        event = asyncio.Event()
        updates = []

        def dispatched(hass, signal, values=None):
            if values is not None:
                updates.append((signal, values))
                event.set()

        with (
            patch(f"{CONNECTION_MODULE}.async_dispatcher_send", side_effect=dispatched),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", new_callable=AsyncMock) as external,
        ):
            await asyncio.gather(one.async_setup_entry(), two.async_setup_entry())
            self.hass.bus.async_listen_once.assert_called_once()
            external.assert_not_called()
            publisher = MQTTClient(config={"auto_reconnect": False})
            await publisher.connect(f"mqtt://ccu:secret@127.0.0.1:{port}/")
            try:
                await publisher.publish("Maxxi-one/powermeter/telemetry", b'{"power": 125}', qos=1)
                await asyncio.wait_for(event.wait(), 3)
                event.clear()
                await publisher.publish(
                    "Maxxi-two/battery/telemetry",
                    json.dumps(
                        {"batteries": [{"soc": 70, "voltage": 52, "inputPower": 80}], "inputPowerTotal": 80}
                    ).encode(),
                    qos=1,
                )
                await asyncio.wait_for(event.wait(), 3)
            finally:
                await publisher.disconnect()
            state_one = self.hass.data[DOMAIN]["one"]["v2_state"]
            state_two = self.hass.data[DOMAIN]["two"]["v2_state"]
            self.assertEqual(state_one["Pr"], 125)
            self.assertNotIn("Pr", state_two)
            self.assertEqual(state_two["SOC"], 70)
            self.assertEqual(state_two["batteriesInfo"][0]["batteryVoltage"], 52000)
            self.assertEqual(len(updates), 2)
            for entry_id in ("one", "two"):
                stats = self.hass.data[DOMAIN][entry_id][MQTT_RECEIVE_STATS]
                self.assertEqual(stats["received_count"], 1)
                self.assertIsNotNone(stats["last_received"].tzinfo)
                self.assertTrue(stats["last_topic"].startswith(f"Maxxi-{entry_id}/"))
            self.assertEqual(updates[0][0], self.hass.data[DOMAIN]["one"][WEBHOOK_SIGNAL_UPDATE])
            manager = self.hass.data[DOMAIN][MQTT_BROKER_MANAGER]
            await one.async_unload()
            self.assertTrue(manager.running)
            await two.async_unload()
            self.assertFalse(manager.running)
            await one.async_setup_entry()
            self.assertTrue(manager.running)
            stop_handler = self.hass.bus.async_listen_once.call_args.args[1]
            await stop_handler(SimpleNamespace())
            self.assertFalse(manager.running)

    async def test_external_subscriptions_and_cleanup(self):
        connection = self.connection(make_entry())
        unsubscribers = [MagicMock() for _ in range(5)]
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", AsyncMock(side_effect=unsubscribers)) as subscribe,
        ):
            await connection.async_setup_entry()
        self.assertEqual(subscribe.await_count, 5)
        self.assertNotIn(MQTT_BROKER_MANAGER, self.hass.data[DOMAIN])
        await connection.async_unload()
        for unsubscribe in unsubscribers:
            unsubscribe.assert_called_once()

    async def test_real_discovery_command_and_ccu_confirmation(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        connection = self.connection(make_entry("one", True, port))
        await connection.async_setup_entry()
        peer = MQTTClient(config={"auto_reconnect": False})
        await peer.connect(f"mqtt://ccu:secret@127.0.0.1:{port}/")
        state_topic = "Maxxi-one/settings/state"
        command_topic = "Maxxi-one/settings/set"
        config_topic = "homeassistant/number/Maxxi-one/maximum/config"
        ready = asyncio.Event()
        config = {
            "name": "Maximum Output",
            "unique_id": "maximum",
            "device": {"identifiers": ["Maxxi-one"], "sw_version": "2.43.0"},
            "state_topic": state_topic,
            "command_topic": command_topic,
            "value_template": "{{ value_json.maximum }}",
            "command_template": '{"maximum": {{ value }}}',
            "min": 0,
            "max": 2000,
            "step": 10,
        }
        try:
            await peer.subscribe([(command_topic, 0)])
            with patch(f"{CONNECTION_MODULE}.async_dispatcher_send", side_effect=lambda *args: ready.set()):
                # State arrives before discovery; the later subscription must replay it.
                await peer.publish(state_topic, b'{"maximum": 100}', qos=1, retain=True)
                await peer.publish(config_topic, json.dumps(config).encode(), qos=1, retain=True)
                await asyncio.wait_for(ready.wait(), 3)
                spec = next(iter(connection.discovery.specs.values()))
                self.assertEqual(connection.discovery.values[spec.key], "100")

                async def respond():
                    message = await asyncio.wait_for(peer.deliver_message(), 3)
                    self.assertEqual(message.topic, command_topic)
                    self.assertEqual(json.loads(message.data), {"maximum": 500})
                    await peer.publish(state_topic, b'{"maximum": 500}', qos=1, retain=True)

                responder = asyncio.create_task(respond())
                try:
                    entity = DiscoveryNumber(connection.discovery, spec)
                    await asyncio.wait_for(entity.async_set_native_value(500), 3)
                    await responder
                    self.assertEqual(entity.native_value, 500)
                finally:
                    if not responder.done():
                        responder.cancel()
                        await asyncio.gather(responder, return_exceptions=True)
            retained = connection._broker_manager.retained_messages("one")
            self.assertNotIn(command_topic, retained)
        finally:
            await peer.disconnect()

    async def test_second_internal_ccu_replays_preexisting_discovery_and_state(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        first = self.connection(make_entry("one", True, port))
        await first.async_setup_entry()
        peer = MQTTClient(config={"auto_reconnect": False})
        await peer.connect(f"mqtt://ccu:secret@127.0.0.1:{port}/")
        config = {
            "name": "New firmware value",
            "unique_id": "new_value",
            "device": {"identifiers": ["Maxxi-two"]},
            "state_topic": "Maxxi-two/new_value",
            "unit_of_measurement": "W",
        }
        try:
            await peer.publish("Maxxi-two/new_value", b"123", qos=1, retain=True)
            await peer.publish(
                "homeassistant/sensor/Maxxi-two/new_value/config", json.dumps(config).encode(), qos=1, retain=True
            )
            second = self.connection(make_entry("two", True, port))
            with patch(f"{CONNECTION_MODULE}.async_dispatcher_send"):
                await second.async_setup_entry()
            spec = next(iter(second.discovery.specs.values()))
            self.assertEqual(second.discovery.values[spec.key], "123")
            self.assertTrue(second.discovery.available(spec.key))
            self.assertFalse(first.discovery.specs)
        finally:
            await peer.disconnect()

    async def test_external_discovery_and_command_never_retains(self):
        connection = self.connection(make_entry())
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", AsyncMock(return_value=MagicMock())) as subscribe,
        ):
            await connection.async_setup_entry()
            cfg = {
                "name": "Output",
                "device": {"identifiers": ["Maxxi-one"], "sw_version": "2.44.0"},
                "state_topic": "Maxxi-one/limit",
                "command_topic": "Maxxi-one/limit/set",
                "max": 2000,
                "step": 1,
            }
            with patch(f"{CONNECTION_MODULE}.async_dispatcher_send"):
                await connection._external_message_received(
                    SimpleNamespace(topic="homeassistant/number/Maxxi-one/limit/config", payload=json.dumps(cfg))
                )
                await connection._external_message_received(SimpleNamespace(topic="Maxxi-one/limit", payload="100"))
                spec = next(iter(connection.discovery.specs.values()))
                self.assertIn("Maxxi-one/limit", [call.args[1] for call in subscribe.await_args_list])

                async def reply(hass, topic, payload, **kwargs):
                    self.assertFalse(kwargs["retain"])
                    await connection._external_message_received(SimpleNamespace(topic="Maxxi-one/limit", payload="500"))

                with patch(f"{CONNECTION_MODULE}.mqtt.async_publish", AsyncMock(side_effect=reply)) as publish:
                    await DiscoveryNumber(connection.discovery, spec).async_set_native_value(500)
                publish.assert_awaited_once_with(self.hass, "Maxxi-one/limit/set", "500", qos=0, retain=False)

    async def test_discovered_pv_value_updates_original_sensor_and_counts_once(self):
        entry = make_entry()
        connection = self.connection(entry)
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", AsyncMock(return_value=MagicMock())),
        ):
            await connection.async_setup_entry()
            self.hass.data[DOMAIN][entry.entry_id]["v2_state"]["batteriesInfo"] = [{}]
            cfg = {
                "name": "PV Power",
                "device": {"identifiers": ["Maxxi-one"]},
                "state_topic": "Maxxi-one/new/pv",
                "value_template": "{{ value }}",
                "unit_of_measurement": "kW",
            }
            with patch(f"{CONNECTION_MODULE}.async_dispatcher_send") as send:
                await connection._external_message_received(
                    SimpleNamespace(topic="homeassistant/sensor/Maxxi-one/newpv/config", payload=json.dumps(cfg))
                )
                await connection._external_message_received(SimpleNamespace(topic="Maxxi-one/new/pv", payload="1.25"))
            state = self.hass.data[DOMAIN][entry.entry_id]["v2_state"]
            self.assertEqual(state["PV_power_total"], 1250)
            self.assertEqual(self.hass.data[DOMAIN][entry.entry_id][MQTT_RECEIVE_STATS]["received_count"], 1)
            signal = self.hass.data[DOMAIN][entry.entry_id][WEBHOOK_SIGNAL_UPDATE]
            send.assert_any_call(self.hass, signal, state)
            original = PvPower(entry)
            original.hass = self.hass
            await original.handle_update(state)
            self.assertEqual(original.unique_id, "one_pv_power")
            self.assertEqual(original.native_value, 1250)

    async def test_partial_external_setup_failure_unsubscribes(self):
        connection = self.connection(make_entry())
        unsubscribe = MagicMock()
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(
                f"{CONNECTION_MODULE}.mqtt.async_subscribe",
                AsyncMock(side_effect=[unsubscribe, RuntimeError("failed")]),
            ),
        ):
            with self.assertRaises(ConfigEntryNotReady):
                await connection.async_setup_entry()
        unsubscribe.assert_called_once()

    async def test_external_repeated_values_count_as_received_messages(self):
        connection = self.connection(make_entry())
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", AsyncMock(return_value=MagicMock())) as subscribe,
        ):
            await connection.async_setup_entry()
        handler = subscribe.await_args_list[0].args[2]
        message = SimpleNamespace(topic="Maxxi-one/powermeter/telemetry", payload='{"power": 100}')
        with patch(f"{CONNECTION_MODULE}.async_dispatcher_send"):
            await handler(message)
            await handler(message)
            stats = self.hass.data[DOMAIN]["one"][MQTT_RECEIVE_STATS]
            self.assertEqual(stats["received_count"], 2)
            self.assertEqual(stats["last_topic"], message.topic)
            last_received = stats["last_received"]
            await connection.async_unload()
            await handler(message)
            self.assertEqual(stats["received_count"], 2)
            self.assertEqual(stats["last_received"], last_received)

    async def test_missing_external_mqtt_requests_setup_retry(self):
        connection = self.connection(make_entry())
        with patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=False)):
            with self.assertRaises(ConfigEntryNotReady):
                await connection.async_setup_entry()

    async def test_internal_platform_failure_releases_broker(self):
        connection = self.connection(make_entry(internal=True))
        manager = MagicMock()
        manager.async_acquire = AsyncMock()
        manager.async_release = AsyncMock()
        self.hass.config_entries.async_forward_entry_setups.side_effect = RuntimeError("platform failed")
        with patch(f"{CONNECTION_MODULE}.get_broker_manager", return_value=manager):
            with self.assertRaises(ConfigEntryNotReady):
                await connection.async_setup_entry()
        manager.async_release.assert_awaited_once_with("one")

    async def test_malformed_telemetry_and_other_ccu_are_ignored(self):
        connection = self.connection(make_entry())
        with (
            patch(f"{CONNECTION_MODULE}.mqtt.async_wait_for_mqtt_client", AsyncMock(return_value=True)),
            patch(f"{CONNECTION_MODULE}.mqtt.async_subscribe", AsyncMock(return_value=MagicMock())),
        ):
            await connection.async_setup_entry()
        with patch(f"{CONNECTION_MODULE}.async_dispatcher_send") as dispatch:
            for payload in (b"not-json", b"[]", b"{}", b'{"power": "invalid"}'):
                await connection._internal_message_received("Maxxi-one/inverter/telemetry", payload)
            await connection._internal_message_received("Maxxi-other/powermeter/telemetry", b'{"power": 100}')
            dispatch.assert_not_called()
        self.assertEqual(self.hass.data[DOMAIN]["one"][MQTT_RECEIVE_STATS]["received_count"], 0)

    async def test_stale_timeout_dispatches_unavailable(self):
        connection = self.connection(make_entry())
        state = {"unloading": False, WEBHOOK_SIGNAL_STATE: "state"}
        with (
            patch(f"{CONNECTION_MODULE}.asyncio.sleep", AsyncMock()),
            patch(f"{CONNECTION_MODULE}.async_dispatcher_send") as dispatch,
        ):
            await connection._mark_stale_after_timeout(state)
            dispatch.assert_called_once_with(self.hass, "state", None)

    async def test_unload_failure_keeps_connection_active(self):
        entry = make_entry()
        connection = MagicMock()
        connection.async_unload = AsyncMock()
        self.hass.data = {DOMAIN: {entry.entry_id: {"connection": connection}}}
        self.hass.config_entries.async_forward_entry_unload.return_value = False
        self.assertFalse(await async_unload_entry(self.hass, entry))
        connection.async_unload.assert_not_awaited()
        self.assertEqual(self.hass.config_entries.async_forward_entry_unload.await_count, 5)
        self.assertIn(
            Platform.SENSOR,
            [call.args[1] for call in self.hass.config_entries.async_forward_entry_unload.await_args_list],
        )

    async def test_migration_keeps_existing_devices_on_v1(self):
        entry = SimpleNamespace(version=3, minor_version=4, data={})
        self.assertTrue(await async_migrate_entry(self.hass, entry))
        kwargs = self.hass.config_entries.async_update_entry.call_args.kwargs
        self.assertEqual(kwargs["version"], 4)
        self.assertEqual(kwargs["data"][CONF_CCU_VERSION], CCU_V1)
