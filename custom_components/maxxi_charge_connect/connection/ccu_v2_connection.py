"""CCU V2 telemetry through the internal broker or Home Assistant MQTT."""

import asyncio
import json
import logging
from types import SimpleNamespace

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from ..const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_MQTT_BROKER,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_TIMEOUT_RECEIVE,
    DOMAIN,
    MQTT_DIAGNOSTICS_SIGNAL,
    MQTT_DISCOVERY_COORDINATOR,
    MQTT_RECEIVE_STATS,
    MQTT_SENSOR_VALUES,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
)
from ..mqtt_broker_manager import MqttBrokerConfig
from ..mqtt_runtime import get_broker_manager
from .ccu_base_connection import CcuBaseConnection
from .ccu_v2_parser import SUBSCRIPTIONS
from .mqtt_discovery import DISCOVERY_FILTERS, PLATFORMS, MqttDiscovery

_LOGGER = logging.getLogger(__name__)


class CCUv2Connection(CcuBaseConnection):
    """Route only this CCU's telemetry to its sensor dispatcher."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry)
        self.base_topic = self.entry.data.get(CONF_DEVICE_ID)
        self._broker_manager = None
        self._handlers = {}
        self._subscribed_topics = set()
        self._topic_unsubscribers = {}
        self.discovery = None

    async def async_setup(self) -> None:
        raise NotImplementedError

    async def async_setup_entry(self) -> bool:
        if not self.base_topic or any(char in self.base_topic for char in "+#\x00"):
            raise ConfigEntryNotReady("CCU V2 requires a valid device ID for MQTT topics")

        entry_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(self.entry.entry_id, {})
        entry_data.update(
            {
                "v2_state": {"deviceId": self.base_topic},
                "mqtt_stale_task": None,
                "unloading": False,
                "mqtt_unsubscribers": [],
                MQTT_RECEIVE_STATS: {
                    "received_count": 0,
                    "last_received": None,
                    "last_topic": None,
                    "started_at": dt_util.utcnow(),
                },
                MQTT_DIAGNOSTICS_SIGNAL: f"{DOMAIN}_{self.entry.entry_id}_mqtt_diagnostics",
                WEBHOOK_SIGNAL_UPDATE: f"{DOMAIN}_{self.entry.entry_id}_update",
                WEBHOOK_SIGNAL_STATE: f"{DOMAIN}_{self.entry.entry_id}_state",
            }
        )
        self._handlers = {
            f"{self.base_topic}/{suffix}": self._create_message_handler(entry_data, parser)
            for suffix, parser in SUBSCRIPTIONS.items()
        }
        _LOGGER.info(
            "CCU V2 %s uses %s MQTT; expected topics: %s",
            self.base_topic,
            "internal" if self.entry.data.get(CONF_ENABLE_MQTT_BROKER, False) else "external",
            ", ".join(self._handlers),
        )
        try:
            self.discovery = MqttDiscovery(
                self.hass, self.entry, self._subscribe_topic, self._publish, self._unsubscribe_topic
            )
            entry_data[MQTT_DISCOVERY_COORDINATOR] = self.discovery
            await self.discovery.async_load()
            if self.entry.data.get(CONF_ENABLE_MQTT_BROKER, False):
                config = MqttBrokerConfig(
                    username=self.entry.data.get(CONF_MQTT_USERNAME, ""),
                    password=self.entry.data.get(CONF_MQTT_PASSWORD, ""),
                    port=self.entry.data.get(CONF_MQTT_PORT, 1883),
                )
                manager = get_broker_manager(self.hass)
                await manager.async_acquire(self.entry.entry_id, config, self._internal_message_received)
                self._broker_manager = manager
            else:
                if not await mqtt.async_wait_for_mqtt_client(self.hass):
                    raise ConfigEntryNotReady("Configure the Home Assistant MQTT integration for the external broker")
            await self.hass.config_entries.async_forward_entry_setups(
                self.entry, [Platform(name) for name in PLATFORMS]
            )
            for topic in self._handlers:
                await self._subscribe_topic(topic)
            await self.discovery.async_start()
        except BaseException as err:
            await self.async_unload()
            if isinstance(err, (asyncio.CancelledError, ConfigEntryNotReady)):
                raise
            if not isinstance(err, Exception):
                raise
            raise ConfigEntryNotReady("CCU V2 MQTT setup failed; check broker configuration and port") from err
        return True

    async def _internal_message_received(self, topic: str, payload: bytes) -> None:
        if self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {}).get("unloading", True):
            return
        accepted = await self.discovery.async_receive(topic, payload) if self.discovery else False
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        projected = accepted and self.discovery.update_legacy_state(entry_data["v2_state"])
        handler = self._handlers.get(topic)
        legacy_accepted = False
        if handler is not None:
            legacy_accepted = await handler(SimpleNamespace(topic=topic, payload=payload))
        if accepted and not legacy_accepted:
            self._record_received(topic)
            if projected:
                async_dispatcher_send(self.hass, entry_data[WEBHOOK_SIGNAL_UPDATE], dict(entry_data["v2_state"]))
        elif handler is None and not accepted:
            _LOGGER.debug("MQTT topic %s does not match a telemetry topic for CCU %s", topic, self.base_topic)

    async def _external_message_received(self, message) -> None:
        await self._internal_message_received(message.topic, message.payload)

    async def _subscribe_topic(self, topic: str) -> None:
        if topic in self._subscribed_topics:
            return
        self._subscribed_topics.add(topic)
        if self._broker_manager is not None:
            # aMQTT sends live publications to our plugin; replay its retained
            # messages for exact subscriptions added by discovery as well.
            retained = self._broker_manager.retained_messages(self.entry.entry_id)
            if topic in retained:
                await self._internal_message_received(topic, retained[topic])
            elif topic in DISCOVERY_FILTERS:
                for retained_topic, payload in retained.items():
                    parts = retained_topic.split("/")
                    if len(parts) == len(topic.split("/")) and parts[0] == "homeassistant" and parts[-1] == "config":
                        await self._internal_message_received(retained_topic, payload)
        else:
            unsubscribe = await mqtt.async_subscribe(self.hass, topic, self._external_message_received, qos=0)
            self._topic_unsubscribers[topic] = unsubscribe
            self.hass.data[DOMAIN][self.entry.entry_id]["mqtt_unsubscribers"].append(unsubscribe)

    def _unsubscribe_topic(self, topic: str) -> None:
        if topic in self._handlers or topic in DISCOVERY_FILTERS:
            return
        self._subscribed_topics.discard(topic)
        unsubscribe = self._topic_unsubscribers.pop(topic, None)
        if unsubscribe is not None:
            unsubscribe()
            callbacks = self.hass.data[DOMAIN][self.entry.entry_id]["mqtt_unsubscribers"]
            callbacks[:] = [callback for callback in callbacks if callback is not unsubscribe]

    async def _publish(self, topic: str, payload: str) -> None:
        if self.discovery is None or not any(
            spec.config.get("command_topic") == topic for spec in self.discovery.specs.values()
        ):
            raise ValueError("Command topic was not advertised by this CCU")
        if self._broker_manager is not None:
            await self._broker_manager.async_publish(self.entry.entry_id, topic, payload.encode("utf-8"))
        else:
            await mqtt.async_publish(self.hass, topic, payload, qos=0, retain=False)

    def _record_received(self, topic: str) -> None:
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        stats = entry_data[MQTT_RECEIVE_STATS]
        stats["received_count"] += 1
        stats["last_received"] = dt_util.utcnow()
        stats["last_topic"] = topic
        async_dispatcher_send(self.hass, entry_data[MQTT_DIAGNOSTICS_SIGNAL])
        stale_task = entry_data.get("mqtt_stale_task")
        if stale_task is not None:
            stale_task.cancel()
        entry_data["mqtt_stale_task"] = self.hass.async_create_background_task(
            self._mark_stale_after_timeout(entry_data), f"MaxxiCharge MQTT timeout {self.entry.entry_id}"
        )

    def _create_message_handler(self, entry_data, parser):
        async def message_received(msg):
            if entry_data.get("unloading"):
                return
            try:
                data = json.loads(msg.payload)
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                values = parser(data)
                if not values:
                    _LOGGER.debug("MQTT topic %s contained no recognized telemetry fields", msg.topic)
                    return
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError, AttributeError) as err:
                _LOGGER.warning("Invalid CCU V2 MQTT telemetry on %s (%s)", msg.topic, type(err).__name__)
                _LOGGER.debug("CCU V2 telemetry parsing failed on %s", msg.topic, exc_info=True)
                return

            direct = values.pop(MQTT_SENSOR_VALUES, None)
            entry_data["v2_state"].update(values)
            if direct:
                entry_data["v2_state"].setdefault(MQTT_SENSOR_VALUES, {}).update(direct)
            if self.discovery:
                # Discovery is authoritative for mapped values. A legacy
                # fallback must not replace PV power with converter input, etc.
                self.discovery.update_legacy_state(entry_data["v2_state"], only_accepted=False)
            self._record_received(msg.topic)
            async_dispatcher_send(self.hass, entry_data[WEBHOOK_SIGNAL_UPDATE], dict(entry_data["v2_state"]))
            return True

        return message_received

    async def _mark_stale_after_timeout(self, entry_data):
        await asyncio.sleep(max(5, self.entry.data.get(CONF_TIMEOUT_RECEIVE, 30)))
        if not entry_data.get("unloading"):
            if self.discovery:
                self.discovery.mark_stale()
            async_dispatcher_send(self.hass, entry_data[WEBHOOK_SIGNAL_STATE], None)

    async def async_unload(self) -> None:
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})
        entry_data["unloading"] = True
        if self.discovery is not None:
            self.discovery.stop()
        for unsubscribe in entry_data.pop("mqtt_unsubscribers", []):
            unsubscribe()
        stale_task = entry_data.pop("mqtt_stale_task", None)
        if stale_task is not None:
            stale_task.cancel()
            try:
                await stale_task
            except asyncio.CancelledError:
                pass
        if self._broker_manager is not None:
            await self._broker_manager.async_release(self.entry.entry_id)
            self._broker_manager = None
        self._handlers.clear()
        self._subscribed_topics.clear()
        self._topic_unsubscribers.clear()
