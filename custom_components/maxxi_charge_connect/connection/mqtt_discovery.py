"""Manage CCU MQTT discovery descriptions, live values, and confirmed writes.

MQTT framing, delivery and retained storage remain the broker library's job.
Only descriptions belonging to the configured CCU and its topic namespace
are accepted here.

Discovery messages are validated before creating entity specifications.
The coordinator tracks state, availability, legacy sensor mappings, and
command acknowledgements without managing the MQTT transport itself.
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

from ..const import CONF_DEVICE_ID, MQTT_SENSOR_VALUES
from .mqtt_errors import mqtt_error
from .mqtt_sensor_bindings import apply_legacy_value, binding_priority, legacy_binding
from .mqtt_sensor_catalog import DERIVED_SOURCES, LOCAL_SENSORS

_LOGGER = logging.getLogger(__name__)
# Supported Home Assistant entity platforms and discovery topic formats.
PLATFORMS = ("sensor", "binary_sensor", "number", "select", "switch")
DISCOVERY_FILTERS = ("homeassistant/+/+/config", "homeassistant/+/+/+/config")
# Limit command confirmation time and the amount of accepted discovery data.
COMMAND_TIMEOUT = 10
# CCU MQTT writes are supported starting with this firmware generation.
MIN_WRITE_FIRMWARE = (2, 43, 0)
MAX_DESCRIPTIONS = 256
MAX_DESCRIPTION_BYTES = 65536

# Expand MQTT discovery's abbreviated configuration keys to canonical names.
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
    """Store a validated discovery entity's identity and configuration.

    Attributes:
        key: Stable identity derived from the discovery topic and entity key.
        source: MQTT topic that supplied this discovery description.
        component: Home Assistant platform associated with the description.
        config: Normalized and validated MQTT discovery configuration.
    """

    key: str
    source: str
    component: str
    config: dict

    @property
    def name(self) -> str:
        """Return the validated human-readable entity name."""
        return self.config["name"]

    @property
    def state_topic(self) -> str:
        """Return the MQTT topic containing the entity's reported state."""
        return self.config["state_topic"]


def _expand(raw: dict) -> dict:
    """Replace supported discovery abbreviations with their full keys.

    Args:
        raw: Incoming MQTT discovery configuration mapping.

    Returns:
        A new mapping with canonical keys and null-valued fields removed.
    """
    return {_ALIASES.get(key, key): value for key, value in raw.items() if value is not None}


def _topic(value, base: str) -> str | None:
    """Expand a discovery topic and reject invalid MQTT topic names.

    Args:
        value: Candidate topic name from discovery configuration.
        base: Topic prefix used to resolve the MQTT ``~`` shorthand.

    Returns:
        The normalized topic, or None for invalid values or wildcards.
    """
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
    """Require an exact device ID segment while allowing vendor topic prefixes.

    Args:
        topic: Fully expanded MQTT topic to inspect.
        device_id: Configured CCU device identifier.

    Returns:
        True if the device identifier occurs as a complete path segment.
    """
    return device_id in topic.split("/")


def parse_discovery(topic: str, payload: bytes | str, device_id: str) -> list[DiscoverySpec]:
    """Parse and validate MQTT entity or device discovery descriptions.

    Both classic per-entity and device-based discovery messages are supported.
    Descriptions are accepted only when their device identifiers and topic
    paths belong to the configured CCU. Malformed or unsupported descriptions
    are skipped independently, within the configured resource limits.

    Args:
        topic: Discovery configuration topic carrying the message.
        payload: JSON description received as bytes or text.
        device_id: Identifier of the configured CCU.

    Returns:
        Validated entity specifications, or an empty list if none qualify.
    """
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
    # Device discovery contains multiple child components; classic discovery
    # describes one entity whose component comes from the MQTT topic.
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
        # Validate platform, device ownership, state topics, and commands before
        # creating an entity. A matching device name alone is insufficient.
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
            # Normalize numeric limits so later control validation can safely
            # rely on finite bounds and a strictly positive step size.
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
    """Coordinate validated CCU discovery, values, and confirmed commands.

    The coordinator restores cached descriptions, manages state subscriptions,
    notifies entity listeners, and exposes discovery-to-sensor mappings.
    Writes are serialized per entity and succeed only after a matching state
    message confirms the requested value.
    """

    def __init__(self, hass, entry, subscribe: Callable[[str], Awaitable[None]], publish, unsubscribe=None) -> None:
        """Initialize discovery state and transport callbacks.

        Args:
            hass: Home Assistant instance used for templates and storage.
            entry: Configuration entry identifying the target CCU.
            subscribe: Async callback for subscribing to an MQTT topic.
            publish: Async callback for publishing an MQTT command.
            unsubscribe: Optional callback for removing topic subscriptions.
        """
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
        self.existing_sensors: dict[str, dict] = {}
        self.native_energy_bindings: dict[str, str] = {}
        self._accepted_keys: set[str] = set()
        self._sources: dict[str, str] = {}
        self._availability: dict[str, bool] = {}
        self._listeners: set[Callable] = set()
        self._mapping_listeners: set[Callable] = set()
        self._platform_listeners: dict[str, Callable] = {}
        self._waiters: dict[str, tuple[str, asyncio.Future]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._config_lock = asyncio.Lock()
        self._templates: dict[str, Template] = {}
        self._stale = True
        self._stopped = False
        self._started = False

    async def async_load(self) -> None:
        """Restore cached discovery descriptions from persistent storage.

        Invalid cache content is ignored. Restored descriptions are validated
        through the same parser used for live discovery messages.
        """
        cached = await self._store.async_load()
        if not isinstance(cached, dict):
            return
        for topic, payload in list(cached.items())[:MAX_DESCRIPTIONS]:
            if isinstance(topic, str) and isinstance(payload, str):
                self._replace_source(topic, payload)
        _LOGGER.debug("Restored %s MQTT discovery entities for CCU %s", len(self.specs), self.device_id)

    async def async_start(self) -> None:
        """Subscribe to discovery topics and all currently known state topics.

        Discovery subscriptions are installed first, followed by the cached
        entity state and availability subscriptions under the config lock.
        """
        self._started = True
        for topic in DISCOVERY_FILTERS:
            await self._subscribe(topic)
        async with self._config_lock:
            await self._subscribe_specs()

    async def _subscribe_specs(self) -> None:
        """Reconcile MQTT subscriptions with current discovery specifications.

        Subscribe to newly needed state and availability topics and remove
        obsolete subscriptions when the transport supports unsubscribing.
        """
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
        """Register a platform for initial and subsequent discovered entities.

        Args:
            component: Home Assistant platform to receive specifications.
            callback: Function called with matching discovery specifications.

        Returns:
            Callback that removes the platform registration.
        """
        self._platform_listeners[component] = callback
        callback([spec for spec in self.specs.values() if spec.component == component])
        return lambda: self._platform_listeners.pop(component, None)

    def add_listener(self, callback: Callable) -> Callable:
        """Register an entity state-change listener.

        Args:
            callback: Function to invoke after relevant state changes.

        Returns:
            Callback that removes the listener.
        """
        self._listeners.add(callback)
        return lambda: self._listeners.discard(callback)

    def add_mapping_listener(self, callback: Callable) -> Callable:
        """Register a listener for discovery-to-sensor mapping changes.

        Args:
            callback: Function to invoke when mapping metadata changes.

        Returns:
            Callback that removes the listener.
        """
        self._mapping_listeners.add(callback)
        return lambda: self._mapping_listeners.discard(callback)

    def _notify_mapping(self):
        """Notify all registered sensor-mapping listeners."""
        for callback in tuple(self._mapping_listeners):
            callback()

    def _notify(self) -> None:
        """Notify all entity listeners to refresh their Home Assistant state."""
        for callback in tuple(self._listeners):
            callback()

    def _replace_source(self, topic: str, payload: str) -> bool:
        """Replace all specifications originating from one discovery topic.

        Removing or changing a description also clears old state values and
        aborts pending commands associated with its former entity keys.
        Platforms and mapping listeners are notified after a valid change.

        Args:
            topic: MQTT discovery configuration topic being updated.
            payload: JSON configuration, or an empty string to remove it.

        Returns:
            True if the accepted source changed; otherwise False.
        """
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
        self._notify_mapping()
        self._notify()
        return True

    async def async_receive(self, topic: str, payload: bytes | str) -> bool:
        """Process an incoming discovery, availability, or state message.

        Discovery updates are parsed and persisted without counting as
        telemetry. Availability messages update online status and can abort
        pending commands. State values are template-rendered and validated
        before being stored or used as command acknowledgements.

        Args:
            topic: MQTT topic on which the message arrived.
            payload: Raw message content as bytes or text.

        Returns:
            True if at least one valid telemetry state was accepted.
        """
        if self._stopped:
            return False
        try:
            text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
        except UnicodeDecodeError:
            return False
        if not isinstance(text, str):
            return False
        if topic.startswith("homeassistant/") and topic.endswith("/config"):
            # Apply discovery changes under a lock to keep subscriptions and
            # the persisted description cache consistent.
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
            # A single incoming topic may supply data for several entities.
            # Only validated values participate in state or command matching.
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
                # A matching observed state confirms the outstanding command.
                waiter[1].set_result(None)
        if accepted:
            self._stale = False
        if matched:
            self._notify()
        return accepted

    def update_legacy_state(self, state: dict, *, only_accepted: bool = True) -> bool:
        """Copy eligible discovered values into the existing sensor state.

        Prefer the highest-priority discovery binding for each legacy sensor.
        By default, only values accepted from the current MQTT message are
        propagated. Derived battery power is updated when both components
        are present.

        Args:
            state: Mutable state dictionary for existing sensor entities.
            only_accepted: Restrict propagation to the most recent message.

        Returns:
            True when at least one existing sensor value changed.
        """
        updated = False
        preferred = {}
        for spec in sorted(self.specs.values(), key=binding_priority):
            binding = legacy_binding(spec)
            if binding is not None:
                preferred[binding.sensor_key] = spec.key
        candidates = self._accepted_keys if only_accepted else self.values.keys()
        for key in sorted(candidates):
            spec = self.specs.get(key)
            binding = legacy_binding(spec) if spec else None
            if spec is not None and binding and preferred.get(binding.sensor_key) == key:
                updated = apply_legacy_value(state, spec, self.values[key]) or updated
        direct = state.get(MQTT_SENSOR_VALUES, {})
        if updated and "battery_power_charge" in direct and "battery_power_discharge" in direct:
            direct["battery_power"] = direct["battery_power_charge"] - direct["battery_power_discharge"]
        return updated

    def register_existing_sensors(self, entities, *, dependencies=None) -> None:
        """Record stable identities and dependencies of existing HA sensors.

        Args:
            entities: Sensors created by the integration's existing factories.
            dependencies: Optional shared source keys for calculated sensors.

        Raises:
            ValueError: If a sensor lacks the expected entry-scoped unique ID.
        """
        prefix = f"{self.entry.entry_id}_"
        for entity in entities:
            if entity.unique_id is None or not entity.unique_id.startswith(prefix):
                raise ValueError("CCU sensor factory produced a sensor without its entry's stable unique ID")
            key = entity.unique_id[len(prefix) :]
            self.existing_sensors[key] = {
                "unique_id": entity.unique_id,
                "class": type(entity).__name__,
                "dependencies": tuple(dependencies) if dependencies is not None else DERIVED_SOURCES.get(key, ()),
                "calculated": dependencies is not None,
                "native_role": getattr(entity, "native_counter_role", None),
            }
        self._notify_mapping()

    def sensor_mapping_report(self) -> dict:
        """Audit coverage of existing sensors by discovery and local sources.

        Classify each registered sensor as local, directly mapped, derived,
        calculated, identity-based, or missing. Dependency chains are resolved
        recursively and cycles are guarded against by the visiting set.

        Returns:
            Dictionary with coverage percentage, per-sensor mapping details,
            missing sensor keys, and unmapped discovery entity names.
        """
        direct = {}
        for spec in self.specs.values():
            binding = legacy_binding(spec)
            if binding:
                direct.setdefault(binding.sensor_key, []).append(spec.name)
        report = {}

        def resolve(key, visiting):
            """Resolve one sensor's coverage using cached and dependent results.

            Args:
                key: Registered sensor key to classify.
                visiting: Keys already visited in the current dependency chain.

            Returns:
                Mapping metadata with the resolved coverage status.
            """
            if key in report:
                return report[key]
            sensor = self.existing_sensors[key]
            sources = direct.get(key, [])
            status = "missing"
            if key in LOCAL_SENSORS:
                status = "local"
            elif sensor["native_role"]:
                native = self.specs.get(self.native_energy_bindings.get(sensor["native_role"]))
                if native:
                    status, sources = "direct", [native.name]
            elif key == "deviceid" and self.specs:
                status, sources = "identity", ["device.identifiers"]
            elif key == "online_status_sensor" and self.specs:
                sources = sorted(
                    {
                        s.state_topic
                        for s in self.specs.values()
                        if (binding := legacy_binding(s)) is not None
                        and (binding.field is not None or binding.dimension == "power")
                    }
                )
                if sources:
                    status = "derived"
            elif sources and not sensor["calculated"]:
                status = "direct"
            elif sensor["dependencies"]:
                deps = sensor["dependencies"]
                if key not in visiting and all(
                    dep in self.existing_sensors and resolve(dep, visiting | {key})["status"] != "missing"
                    for dep in deps
                ):
                    status = "calculated"
            report[key] = {**sensor, "status": status, "discovery": sorted(set(sources))}
            return report[key]

        for key in self.existing_sensors:
            resolve(key, set())
        eligible = [item for item in report.values() if item["status"] != "local"]
        covered = sum(item["status"] != "missing" for item in eligible)
        return {
            "coverage": round(100 * covered / len(eligible), 1) if eligible else 0,
            "sensors": report,
            "missing": [key for key, item in report.items() if item["status"] == "missing"],
            "unmapped_discovery": sorted(
                {
                    s.name
                    for s in self.specs.values()
                    if s.component in ("sensor", "binary_sensor")
                    and legacy_binding(s) is None
                    and s.key not in self.native_energy_bindings.values()
                }
            ),
        }

    def _render(self, source: str | None, payload: str) -> str | None:
        """Evaluate an optional Home Assistant template against an MQTT value.

        Args:
            source: Template text, or None to use the raw payload.
            payload: Incoming MQTT message text.

        Returns:
            Trimmed rendered value, or None if template evaluation fails.
        """
        if source is None:
            return payload.strip()
        try:
            value = self._template(source).async_render_with_possible_json_value(payload, None)
        except (TemplateError, ValueError, TypeError):
            _LOGGER.warning("Could not evaluate a CCU MQTT discovery template")
            return None
        return None if value is None else str(value).strip()

    def _template(self, source: str) -> Template:
        """Return a cached Home Assistant template for the provided source.

        Args:
            source: Jinja template source string.

        Returns:
            Compiled Home Assistant template reused across messages.
        """
        if source not in self._templates:
            self._templates[source] = Template(source, self.hass)
        return self._templates[source]

    def available(self, key: str) -> bool:
        """Check whether a discovered entity currently has usable state.

        An entity must exist, have a received value, and belong to an active,
        non-stale coordinator. Its availability topic must also report online
        when one is configured.

        Args:
            key: Discovery entity key to check.

        Returns:
            True when all availability requirements are satisfied.
        """
        spec = self.specs.get(key)
        if not spec or self._stopped or self._stale or key not in self.values:
            return False
        topic = spec.config.get("availability_topic")
        return topic is None or self._availability.get(topic, False)

    def mark_stale(self) -> None:
        """Mark all telemetry stale and abort outstanding command confirmations.

        Entity listeners are notified so Home Assistant can update their
        availability immediately.
        """
        self._stale = True
        for key in tuple(self._waiters):
            self._cancel_waiter(key, "The CCU stopped responding")
        self._notify()

    def _firmware(self, spec: DiscoverySpec) -> tuple[int, int, int] | None:
        """Determine the CCU firmware version used for write compatibility.

        The device metadata provides a fallback; a live firmware sensor value
        takes precedence when available.

        Args:
            spec: Discovery specification containing device metadata.

        Returns:
            Major, minor, and patch version, or None if not recognizable.
        """
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
        """Compare received state against the expected command result.

        Numeric controls tolerate tiny representation differences, while
        other controls require exact string equality.

        Args:
            spec: Discovery specification defining the entity platform.
            actual: Value received from the CCU state topic.
            expected: State expected after executing the command.

        Returns:
            True when both values represent the same confirmed state.
        """
        if spec.component == "number":
            try:
                return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-6)
            except ValueError:
                return False
        return actual == expected

    async def async_write(self, key: str, value, expected: str) -> None:
        """Publish an authorized CCU command and await state confirmation.

        Writes are serialized by discovery key to avoid concurrent commands
        racing against the same state topic. The method verifies command
        support, firmware compatibility, and entity availability, then renders
        the command payload. A waiter is installed before publishing to avoid
        missing a fast acknowledgement.

        Args:
            key: Discovery entity key whose setting should be changed.
            value: Value passed to the command template or MQTT payload.
            expected: State value that must be observed to confirm the command.

        Raises:
            HomeAssistantError: If the command is unsupported, the CCU is
                unavailable, payload rendering or publishing fails, or no
                matching confirmation arrives before the timeout.
        """
        async with self._locks.setdefault(key, asyncio.Lock()):
            spec = self.specs.get(key)
            if not spec or not spec.config.get("command_topic"):
                raise mqtt_error("mqtt_no_command", "The CCU does not advertise a command topic for this setting")
            if spec.config["command_topic"] == spec.state_topic:
                raise mqtt_error("mqtt_no_separate_state", "A separate state topic is required to confirm CCU commands")
            firmware = self._firmware(spec)
            if firmware is None or firmware < MIN_WRITE_FIRMWARE:
                raise mqtt_error(
                    "mqtt_firmware_unsupported", "MQTT control requires a known CCU firmware version of at least 2.43.0"
                )
            if not self.available(key):
                raise mqtt_error("mqtt_setting_unavailable", "The CCU setting is not available; no command was sent")
            if self._equal(spec, self.values[key], expected):
                # Avoid sending redundant writes when the state already matches.
                return
            template = spec.config.get("command_template")
            try:
                payload = (
                    str(self._template(template).async_render({"value": value}, parse_result=False))
                    if template
                    else str(value)
                )
            except (TemplateError, ValueError, TypeError) as err:
                raise mqtt_error(
                    "mqtt_command_template_invalid", "The CCU command template could not be evaluated"
                ) from err
            future = asyncio.get_running_loop().create_future()
            # Register before publish: the CCU may acknowledge immediately.
            self._waiters[key] = (expected, future)
            try:
                async with asyncio.timeout(COMMAND_TIMEOUT):
                    try:
                        await self._publish(spec.config["command_topic"], payload)
                    except HomeAssistantError:
                        raise
                    except Exception as err:
                        raise mqtt_error("mqtt_publish_failed", "The MQTT command could not be sent") from err
                    await future
            except TimeoutError as err:
                raise mqtt_error(
                    "mqtt_confirmation_timeout",
                    f"The CCU did not confirm '{spec.name}' within {COMMAND_TIMEOUT} seconds",
                    seconds=COMMAND_TIMEOUT,
                ) from err
            finally:
                # Always release the per-command waiter and consume any stored
                # exception so abandoned futures do not emit warnings.
                self._waiters.pop(key, None)
                if not future.done():
                    future.cancel()
                elif not future.cancelled():
                    future.exception()

    def _cancel_waiter(self, key: str, reason: str) -> None:
        """Fail an unfinished command confirmation with an MQTT error.

        Args:
            key: Discovery key associated with a pending command.
            reason: Human-readable explanation for aborting the command.
        """
        waiter = self._waiters.get(key)
        if waiter and not waiter[1].done():
            waiter[1].set_exception(mqtt_error("mqtt_command_aborted", reason))

    def stop(self) -> None:
        """Stop discovery updates and invalidate remaining entity state.

        Repeated calls are safe. Pending writes are aborted, entity listeners
        are notified through stale-state handling, and platform registrations
        are removed.
        """
        if self._stopped:
            return
        self._stopped = True
        self.mark_stale()
        self._platform_listeners.clear()
