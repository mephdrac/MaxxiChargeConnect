"""CCU discovery descriptions, live values and confirmed command handling.

MQTT framing, delivery and retained storage remain the broker library's job.
Only descriptions belonging to the configured CCU and its topic namespace
are accepted here.
"""

import asyncio
import json
import logging
import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import Template

from ..const import CONF_DEVICE_ID
from .mqtt_sensor_bindings import apply_legacy_value

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ("sensor", "binary_sensor", "number", "select", "switch")
DISCOVERY_FILTERS = ("homeassistant/+/+/config", "homeassistant/+/+/+/config")
COMMAND_TIMEOUT = 10
# CCU MQTT writes are supported starting with this firmware generation.
MIN_WRITE_FIRMWARE = (2, 43, 0)
MAX_DESCRIPTIONS = 256
MAX_DESCRIPTION_BYTES = 65536

_ALIASES = {
    "stat_t": "state_topic",
    "cmd_t": "command_topic",
    "val_tpl": "value_template",
    "cmd_tpl": "command_template",
    "avty_t": "availability_topic",
    "avty_tpl": "availability_template",
    "pl_avail": "payload_available",
    "pl_not_avail": "payload_not_available",
    "uniq_id": "unique_id",
    "dev": "device",
    "p": "platform",
    "ops": "options",
    "pl_on": "payload_on",
    "pl_off": "payload_off",
    "stat_on": "state_on",
    "stat_off": "state_off",
    "dev_cla": "device_class",
    "stat_cla": "state_class",
    "unit_of_meas": "unit_of_measurement",
    "ent_cat": "entity_category",
    "avty": "availability",
}


@dataclass(frozen=True)
class DiscoverySpec:
    """One entity's validated discovery configuration."""

    key: str
    source: str
    component: str
    config: dict

    @property
    def name(self) -> str:
        return self.config["name"]

    @property
    def state_topic(self) -> str:
        return self.config["state_topic"]


def _expand(raw: dict) -> dict:
    return {_ALIASES.get(key, key): value for key, value in raw.items() if value is not None}


def _topic(value, base: str) -> str | None:
    if not isinstance(value, str):
        return None
    if value.startswith("~"):
        value = base + value[1:]
    elif value.endswith("~"):
        value = value[:-1] + base
    if not value or any(char in value for char in "+#\x00"):
        return None
    return value


def _belongs_to_device(topic: str, device_id: str) -> bool:
    """Allow vendor prefixes while requiring an exact device path segment."""
    return device_id in topic.split("/")


def parse_discovery(topic: str, payload: bytes | str, device_id: str) -> list[DiscoverySpec]:
    """Normalize entity and device discovery, with exact CCU ownership checks."""
    parts = topic.split("/")
    if len(parts) not in (4, 5) or parts[0] != "homeassistant" or parts[-1] != "config":
        return []
    if not payload or len(payload.encode("utf-8") if isinstance(payload, str) else payload) > MAX_DESCRIPTION_BYTES:
        return []
    try:
        raw = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(raw, dict):
        return []
    root = _expand(raw)
    components = root.get("components", root.get("cmps"))
    if parts[1] == "device":
        if not isinstance(components, dict):
            return []
        configs = [(str(key), _expand(value)) for key, value in components.items() if isinstance(value, dict)]
    else:
        configs = [("", {**root, "platform": parts[1]})]

    specs = []
    for component_key, child in configs[:MAX_DESCRIPTIONS]:
        cfg = {**root, **child}
        component = cfg.get("platform")
        if component not in PLATFORMS:
            continue
        device = cfg.get("device")
        if not isinstance(device, dict):
            continue
        identifiers = device.get("identifiers", device.get("ids", []))
        if isinstance(identifiers, str):
            identifiers = [identifiers]
        if not isinstance(identifiers, list) or device_id.casefold() not in {
            item.casefold() for item in identifiers if isinstance(item, str)
        }:
            continue
        base = cfg.get("~", "")
        if not isinstance(base, str):
            continue
        valid = True
        for key in ("state_topic", "command_topic", "availability_topic"):
            if key not in cfg:
                continue
            value = _topic(cfg[key], base)
            if value is None or not _belongs_to_device(value, device_id):
                valid = False
                break
            cfg[key] = value
        if not valid or not cfg.get("state_topic"):
            continue
        if component in ("number", "select", "switch") and not cfg.get("command_topic"):
            continue
        # A single availability description is supported; never silently ignore
        # more complex availability rules advertised by firmware.
        availability = cfg.get("availability")
        if availability is not None:
            if not isinstance(availability, list) or len(availability) != 1 or not isinstance(availability[0], dict):
                continue
            avail = _expand(availability[0])
            avail_topic = _topic(avail.get("topic", avail.get("t")), base)
            if not avail_topic or not _belongs_to_device(avail_topic, device_id):
                continue
            cfg["availability_topic"] = avail_topic
            if "value_template" in avail:
                if not isinstance(avail["value_template"], str):
                    continue
                cfg["availability_template"] = avail["value_template"]
            for key in ("payload_available", "payload_not_available"):
                if key in avail:
                    cfg[key] = avail[key]
        name = cfg.get("name", component_key or parts[-2])
        if name is None:
            name = component_key or parts[-2]
        if not isinstance(name, str) or not name.strip():
            continue
        cfg["name"] = name
        if any(
            key in cfg and not isinstance(cfg[key], str)
            for key in (
                "value_template",
                "command_template",
                "availability_template",
                "device_class",
                "state_class",
                "unit_of_measurement",
                "entity_category",
            )
        ):
            continue
        if component == "select" and (
            not isinstance(cfg.get("options"), list)
            or not cfg["options"]
            or not all(isinstance(option, str) for option in cfg["options"])
        ):
            continue
        if component == "number":
            try:
                cfg.update(
                    {key: float(cfg.get(key, default)) for key, default in (("min", 0), ("max", 100), ("step", 1))}
                )
            except (ValueError, TypeError):
                continue
            if (
                not all(math.isfinite(cfg[key]) for key in ("min", "max", "step"))
                or cfg["min"] > cfg["max"]
                or cfg["step"] <= 0
            ):
                continue
        unique_id = child.get("unique_id") or component_key or cfg.get("unique_id") or parts[-2]
        if not isinstance(unique_id, str):
            continue
        cfg["device"] = device
        # Topic and component identify an entity even if its human-readable name changes.
        key = f"{topic}|{component}|{unique_id}"
        specs.append(DiscoverySpec(key, topic, component, cfg))
    return specs


class MqttDiscovery:
    """Cache descriptions, evaluate values, and wait for command acknowledgements."""

    def __init__(self, hass, entry, subscribe: Callable[[str], Awaitable[None]], publish, unsubscribe=None) -> None:
        self.hass = hass
        self.entry = entry
        self.device_id = entry.data[CONF_DEVICE_ID]
        self._subscribe = subscribe
        self._publish = publish
        self._unsubscribe = unsubscribe
        self._topics: set[str] = set()
        self._store = Store(hass, 1, f"maxxi_charge_connect_mqtt_discovery_{entry.entry_id}")
        self.specs: dict[str, DiscoverySpec] = {}
        self.values: dict[str, str] = {}
        self.entity_claims: dict[tuple, str] = {}
        self._accepted_keys: set[str] = set()
        self._sources: dict[str, str] = {}
        self._availability: dict[str, bool] = {}
        self._listeners: set[Callable] = set()
        self._platform_listeners: dict[str, Callable] = {}
        self._waiters: dict[str, tuple[str, asyncio.Future]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._config_lock = asyncio.Lock()
        self._templates: dict[str, Template] = {}
        self._stale = True
        self._stopped = False
        self._started = False

    async def async_load(self) -> None:
        cached = await self._store.async_load()
        if not isinstance(cached, dict):
            return
        for topic, payload in list(cached.items())[:MAX_DESCRIPTIONS]:
            if isinstance(topic, str) and isinstance(payload, str):
                self._replace_source(topic, payload)
        _LOGGER.debug("Restored %s MQTT discovery entities for CCU %s", len(self.specs), self.device_id)

    async def async_start(self) -> None:
        self._started = True
        for topic in DISCOVERY_FILTERS:
            await self._subscribe(topic)
        async with self._config_lock:
            await self._subscribe_specs()

    async def _subscribe_specs(self) -> None:
        topics = {spec.state_topic for spec in self.specs.values()}
        topics.update(
            spec.config["availability_topic"] for spec in self.specs.values() if spec.config.get("availability_topic")
        )
        previous = self._topics
        self._topics = topics
        if self._unsubscribe:
            for topic in previous - topics:
                self._unsubscribe(topic)
        for topic in sorted(topics - previous):
            await self._subscribe(topic)

    def add_platform(self, component: str, callback: Callable) -> Callable:
        self._platform_listeners[component] = callback
        callback([spec for spec in self.specs.values() if spec.component == component])
        return lambda: self._platform_listeners.pop(component, None)

    def add_listener(self, callback: Callable) -> Callable:
        self._listeners.add(callback)
        return lambda: self._listeners.discard(callback)

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            callback()

    def _replace_source(self, topic: str, payload: str) -> bool:
        if not payload and topic not in self._sources:
            return False
        specs = parse_discovery(topic, payload, self.device_id) if payload else []
        if payload and not specs:
            return False
        existing = {key for key, spec in self.specs.items() if spec.source == topic}
        if len(self.specs) - len(existing) + len(specs) > MAX_DESCRIPTIONS:
            return False
        if self._sources.get(topic) == payload:
            return False
        self._templates.clear()
        for key in existing:
            self.specs.pop(key)
            self.values.pop(key, None)
            self._cancel_waiter(key, "The CCU changed its MQTT discovery description")
        if payload:
            self._sources[topic] = payload
        else:
            self._sources.pop(topic, None)
        for spec in specs:
            self.specs[spec.key] = spec
        _LOGGER.debug(
            "CCU %s discovery updated from %s; %s entities configured", self.device_id, topic, len(self.specs)
        )
        for component, callback in tuple(self._platform_listeners.items()):
            callback([spec for spec in self.specs.values() if spec.component == component])
        self._notify()
        return True

    async def async_receive(self, topic: str, payload: bytes | str) -> bool:
        """Return whether a live state was accepted (discovery itself is not telemetry)."""
        if self._stopped:
            return False
        try:
            text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
        except UnicodeDecodeError:
            return False
        if not isinstance(text, str):
            return False
        if topic.startswith("homeassistant/") and topic.endswith("/config"):
            async with self._config_lock:
                if self._replace_source(topic, text):
                    self._store.async_delay_save(lambda: dict(self._sources), 1)
                    if self._started:
                        await self._subscribe_specs()
            return False
        accepted = False
        matched = False
        self._accepted_keys.clear()
        for key, spec in tuple(self.specs.items()):
            cfg = spec.config
            if topic == cfg.get("availability_topic"):
                matched = True
                value = self._render(cfg.get("availability_template"), text)
                if value == str(cfg.get("payload_available", "online")):
                    self._availability[topic] = True
                elif value == str(cfg.get("payload_not_available", "offline")):
                    self._availability[topic] = False
                    self._cancel_waiter(key, "The CCU reported that it is offline")
            if topic != spec.state_topic:
                continue
            matched = True
            value = self._render(cfg.get("value_template"), text)
            if value is None or value.lower() in ("", "unknown", "unavailable", "none", "null"):
                continue
            if spec.component == "select" and value not in cfg["options"]:
                continue
            if spec.component in ("binary_sensor", "switch"):
                on = cfg.get("state_on", cfg.get("payload_on", "ON"))
                off = cfg.get("state_off", cfg.get("payload_off", "OFF"))
                if value not in (str(on), str(off)):
                    continue
            if spec.component in ("number", "sensor") and (
                spec.component == "number" or cfg.get("unit_of_measurement") or cfg.get("state_class")
            ):
                try:
                    if not math.isfinite(float(value)):
                        continue
                except ValueError:
                    continue
            self.values[key] = value
            self._accepted_keys.add(key)
            accepted = True
            waiter = self._waiters.get(key)
            if waiter and not waiter[1].done() and self._equal(spec, value, waiter[0]):
                waiter[1].set_result(None)
        if accepted:
            self._stale = False
        if matched:
            self._notify()
        return accepted

    def update_legacy_state(self, state: dict) -> bool:
        """Feed only values accepted in this message to existing sensor entities."""
        updated = False
        for key in self._accepted_keys:
            spec = self.specs.get(key)
            if spec is not None:
                updated = apply_legacy_value(state, spec, self.values[key]) or updated
        return updated

    def _render(self, source: str | None, payload: str) -> str | None:
        if source is None:
            return payload.strip()
        try:
            value = self._template(source).async_render_with_possible_json_value(payload, None)
        except (TemplateError, ValueError, TypeError):
            _LOGGER.warning("Could not evaluate a CCU MQTT discovery template")
            return None
        return None if value is None else str(value).strip()

    def _template(self, source: str) -> Template:
        if source not in self._templates:
            self._templates[source] = Template(source, self.hass)
        return self._templates[source]

    def available(self, key: str) -> bool:
        spec = self.specs.get(key)
        if not spec or self._stopped or self._stale or key not in self.values:
            return False
        topic = spec.config.get("availability_topic")
        return topic is None or self._availability.get(topic, False)

    def mark_stale(self) -> None:
        self._stale = True
        for key in tuple(self._waiters):
            self._cancel_waiter(key, "The CCU stopped responding")
        self._notify()

    def _firmware(self, spec: DiscoverySpec) -> tuple[int, int, int] | None:
        device = spec.config.get("device", {})
        version = device.get("sw_version", device.get("sw"))
        for key, candidate in self.specs.items():
            if candidate.name.casefold() in ("ccu ver", "firmware", "firmware version") and key in self.values:
                version = self.values[key]
                break
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(version))
        return (int(match[1]), int(match[2]), int(match[3] or 0)) if match else None

    @staticmethod
    def _equal(spec: DiscoverySpec, actual: str, expected: str) -> bool:
        if spec.component == "number":
            try:
                return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-6)
            except ValueError:
                return False
        return actual == expected

    async def async_write(self, key: str, value, expected: str) -> None:
        """Serialize writes per entity; register the waiter before publishing."""
        async with self._locks.setdefault(key, asyncio.Lock()):
            spec = self.specs.get(key)
            if not spec or not spec.config.get("command_topic"):
                raise HomeAssistantError("The CCU does not advertise a command topic for this setting")
            if spec.config["command_topic"] == spec.state_topic:
                raise HomeAssistantError("A separate state topic is required to confirm CCU commands")
            firmware = self._firmware(spec)
            if firmware is None or firmware < MIN_WRITE_FIRMWARE:
                raise HomeAssistantError("MQTT control requires a known CCU firmware version of at least 2.43.0")
            if not self.available(key):
                raise HomeAssistantError("The CCU setting is not available; no command was sent")
            if self._equal(spec, self.values[key], expected):
                return
            template = spec.config.get("command_template")
            try:
                payload = (
                    str(self._template(template).async_render({"value": value}, parse_result=False))
                    if template
                    else str(value)
                )
            except (TemplateError, ValueError, TypeError) as err:
                raise HomeAssistantError("The CCU command template could not be evaluated") from err
            future = asyncio.get_running_loop().create_future()
            self._waiters[key] = (expected, future)
            try:
                async with asyncio.timeout(COMMAND_TIMEOUT):
                    try:
                        await self._publish(spec.config["command_topic"], payload)
                    except HomeAssistantError:
                        raise
                    except Exception as err:
                        raise HomeAssistantError("The MQTT command could not be sent") from err
                    await future
            except TimeoutError as err:
                raise HomeAssistantError(
                    f"The CCU did not confirm '{spec.name}' within {COMMAND_TIMEOUT} seconds"
                ) from err
            finally:
                self._waiters.pop(key, None)
                if not future.done():
                    future.cancel()
                elif not future.cancelled():
                    future.exception()

    def _cancel_waiter(self, key: str, reason: str) -> None:
        waiter = self._waiters.get(key)
        if waiter and not waiter[1].done():
            waiter[1].set_exception(HomeAssistantError(reason))

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self.mark_stale()
        self._platform_listeners.clear()
