"""Real MQTT lifecycle tests; runnable without a Home Assistant installation.

Run: python -m unittest discover -s tests -p test_mqtt_broker_manager.py
"""

import asyncio
import importlib.util
import socket
import sys
import unittest
from pathlib import Path

from amqtt.client import MQTTClient
from amqtt.errors import BrokerError

# Load only the manager: the integration package itself requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "maxxi_mqtt_manager_under_test",
    Path(__file__).resolve().parents[1] / "custom_components/maxxi_charge_connect/mqtt_broker_manager.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
MqttBrokerConfig = _MODULE.MqttBrokerConfig
MqttBrokerManager = _MODULE.MqttBrokerManager


class MqttBrokerManagerTests(unittest.IsolatedAsyncioTestCase):
    """Exercise actual listeners, clients, authentication and port reuse."""

    async def asyncSetUp(self):
        self.manager = MqttBrokerManager()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.config = MqttBrokerConfig("ccu", "secret", self.port, "127.0.0.1")
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.disconnect()
        await self.manager.async_shutdown()

    async def connect(self, credentials="ccu:secret@"):
        client = MQTTClient(config={"auto_reconnect": False, "connection_timeout": 1})
        self.clients.append(client)
        await asyncio.wait_for(client.connect(f"mqtt://{credentials}127.0.0.1:{self.port}/"), 3)
        return client

    async def test_multiple_ccus_exchange_messages_and_release_last(self):
        await asyncio.gather(
            self.manager.async_acquire("ccu1", self.config),
            self.manager.async_acquire("ccu2", self.config),
        )
        await self.manager.async_acquire("ccu1", self.config)
        receiver = await self.connect()
        sender = await self.connect()
        await receiver.subscribe([("ccu/test", 1)])
        await sender.publish("ccu/test", b"hello", qos=1)
        message = await asyncio.wait_for(receiver.deliver_message(), 3)
        self.assertEqual(message.data, b"hello")
        await self.manager.async_release("ccu1")
        self.assertTrue(self.manager.running)
        for client in self.clients:
            await client.disconnect()
        self.clients.clear()
        await self.manager.async_release("ccu2")
        self.assertFalse(self.manager.running)
        await self.manager.async_release("ccu2")
        await self.manager.async_acquire("ccu1", self.config)
        self.assertTrue(self.manager.running)

    async def test_invalid_and_anonymous_credentials_rejected(self):
        await self.manager.async_acquire("ccu1", self.config)

        # Check the protocol-level CONNACK rejection and socket closure directly.
        def mqtt_string(value):
            encoded = value.encode()
            return len(encoded).to_bytes(2, "big") + encoded

        for username, password in ((None, None), ("ccu", "wrong"), ("wrong", "secret")):
            with self.subTest(username=username):
                reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
                try:
                    flags = 2 if username is None else 194
                    payload = mqtt_string("auth-test")
                    if username is not None:
                        payload += mqtt_string(username) + mqtt_string(password)
                    body = mqtt_string("MQTT") + bytes([4, flags, 0, 10]) + payload
                    writer.write(bytes([16, len(body)]) + body)
                    await writer.drain()
                    self.assertEqual(await asyncio.wait_for(reader.readexactly(4), 3), b"\x20\x02\x00\x05")
                    self.assertEqual(await asyncio.wait_for(reader.read(1), 3), b"")
                finally:
                    writer.close()
                    await writer.wait_closed()
        await self.connect()

    async def test_conflicting_settings_do_not_disrupt_running_broker(self):
        await self.manager.async_acquire("ccu1", self.config)
        with self.assertRaises(ValueError):
            await self.manager.async_acquire("ccu2", MqttBrokerConfig("ccu", "different", self.port))
        await self.connect()

    async def test_occupied_port_can_be_retried(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", self.port))
            listener.listen()
            with self.assertLogs("amqtt.broker", level="ERROR"):
                with self.assertRaises(BrokerError):
                    await self.manager.async_acquire("ccu1", self.config)
        self.assertFalse(self.manager.running)
        await self.manager.async_acquire("ccu1", self.config)
        await self.connect()

    async def test_shutdown_with_active_client_and_restart(self):
        await self.manager.async_acquire("ccu1", self.config)
        await self.connect()
        await self.manager.async_shutdown()
        self.assertFalse(self.manager.running)
        await self.manager.async_shutdown()
        await self.manager.async_acquire("ccu2", self.config)
        await self.connect()

    def test_invalid_configuration_and_password_repr(self):
        for port in (0, 65536, True, "1883"):
            with self.assertRaises(ValueError):
                MqttBrokerConfig("ccu", "secret", port)
        with self.assertRaises(ValueError):
            MqttBrokerConfig("ccu", "")
        self.assertNotIn("secret", repr(self.config))
