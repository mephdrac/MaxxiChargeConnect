"""Home Assistant entities backed by CCU-provided MQTT discovery descriptions.

This module provides entity implementations for MQTT discovery descriptions
published by a CCU device.

It supports the following Home Assistant platforms:
- Sensor
- Binary sensor
- Number
- Select
- Switch

Discovered entities share a common coordinator that manages their
configuration, current values, availability, and state updates.

Existing sensor implementations remain responsible for regular telemetry.
Native CCU energy counters are handled separately to preserve their
original measurements and entity identities.
"""

import hashlib
import math

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from ..connection.mqtt_errors import mqtt_error
from ..connection.mqtt_sensor_bindings import binding_priority, legacy_binding, measurement_identity, native_energy_key
from ..connection.mqtt_sensor_catalog import register_sensors
from ..const import DOMAIN, MQTT_DISCOVERY_COORDINATOR
from .ccu_native_energy import CcuNativeEnergySensor

# Map CCU control descriptions to Home Assistant translation keys.
# These mappings ensure that known controls use localized entity names
# instead of the names provided directly by MQTT discovery.
_CONTROL_TRANSLATIONS = {
    ("number", "minimum soc"): "mqtt_minimum_soc",
    ("number", "maximum soc"): "mqtt_maximum_soc",
    ("number", "maximum output"): "mqtt_maximum_output",
    ("number", "meter loss output"): "mqtt_meter_loss_output",
    ("number", "maximum charging power"): "mqtt_maximum_charging_power",
    ("select", "charging strategy"): "mqtt_charging_strategy",
    ("switch", "ups mode"): "mqtt_ups_mode",
}


def _unique_id(entry_id, spec):
    """Generate a stable unique identifier for a discovered MQTT entity.

    The identifier combines the Home Assistant configuration entry ID
    with a shortened SHA-256 hash of the discovery specification key.

    Using a hash prevents excessively long identifiers while keeping
    the entity identity independent of its displayed name.

    Args:
        entry_id: Home Assistant configuration entry identifier.
        spec: MQTT discovery specification containing the entity key.

    Returns:
        str: Stable unique identifier for the discovered entity.
    """
    digest = hashlib.sha256(spec.key.encode()).hexdigest()[:24]
    return f"{entry_id}_mqtt_discovery_{digest}"


def _disable_old_duplicate(hass, entry, spec, *, duplicate=True):
    """Disable or restore a previously generated duplicate discovery entity.

    The entity registry is checked for an existing entity with the
    generated discovery identifier.

    Only entities belonging to the current configuration entry are
    modified. This prevents changes to unrelated integrations or devices.

    When a duplicate is detected, the corresponding entity is disabled
    by the integration without deleting its registry entry or history.

    An entity previously disabled by the integration can be enabled
    again when it is no longer considered a duplicate.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry associated with the CCU device.
        spec: MQTT discovery specification identifying the entity.
        duplicate: Whether the entity should be treated as a duplicate.
            Defaults to True.

    Returns:
        None: The entity registry is updated when applicable.
    """
    registry = er.async_get(hass)

    entity_id = registry.async_get_entity_id(
        spec.component,
        DOMAIN,
        _unique_id(entry.entry_id, spec),
    )

    if entity_id is None:
        return

    entity = registry.async_get(entity_id)

    if entity is None or entity.config_entry_id != entry.entry_id:
        return

    if duplicate and entity.disabled_by is None:
        registry.async_update_entity(
            entity_id,
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        )

    elif not duplicate and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
        registry.async_update_entity(
            entity_id,
            disabled_by=None,
        )


class DiscoveryEntity(Entity):
    """Provide common functionality for MQTT-discovered Home Assistant entities.

    This base class manages the identity, metadata, availability,
    state updates, and lifecycle of entities created from CCU MQTT
    discovery descriptions.

    Entity values and configurations are obtained from the shared
    discovery coordinator.

    Subclasses implement platform-specific behavior for sensors,
    binary sensors, numbers, selects, and switches.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, spec) -> None:
        """Initialize an entity from an MQTT discovery specification.

        Store the discovery key and initial specification, generate a
        stable entity identifier, and associate the entity with the
        corresponding Home Assistant device.

        Known control entities receive translation keys so that
        Home Assistant can provide localized names.

        Args:
            coordinator: MQTT discovery coordinator managing specifications,
                values, availability, and entity updates.
            spec: Discovery specification describing the entity.
        """
        self.coordinator = coordinator
        self._initial_spec = spec
        self.key = spec.key

        self._attr_unique_id = _unique_id(
            coordinator.entry.entry_id,
            spec,
        )

        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.entry.entry_id)}}

        key = _CONTROL_TRANSLATIONS.get((spec.component, spec.name.casefold().strip()))

        if key is not None:
            self._attr_translation_key = key

    @property
    def spec(self):
        """Return the current discovery specification for this entity.

        The latest specification is retrieved from the coordinator.
        If the specification is no longer available, the initial
        specification is used as a fallback.

        This allows entity properties to reflect updated MQTT
        discovery information without recreating the entity.

        Returns:
            The current or initially received discovery specification.
        """
        return self.coordinator.specs.get(
            self.key,
            self._initial_spec,
        )

    @property
    def name(self):
        """Return the displayed name of the discovered entity.

        Known control entities use the translated Home Assistant name
        once they are associated with a platform.

        All other entities retain the name provided by their
        MQTT discovery specification.

        Returns:
            str: Localized control name or CCU-provided entity name.
        """
        if (
            self.platform is not None
            and (
                self.spec.component,
                self.spec.name.casefold().strip(),
            )
            in _CONTROL_TRANSLATIONS
        ):
            return super().name

        return self.spec.name

    @property
    def entity_category(self):
        """Determine the Home Assistant category of the entity.

        Explicit configuration and diagnostic categories from the
        discovery specification take precedence.

        Number, select, and switch entities default to the
        configuration category because they represent adjustable
        device settings.

        Other entities have no category unless explicitly configured.

        Returns:
            EntityCategory | None: Configuration or diagnostic category,
            or None if no category applies.
        """
        category = self.spec.config.get("entity_category")

        if category in (
            EntityCategory.CONFIG,
            EntityCategory.DIAGNOSTIC,
        ):
            return EntityCategory(category)

        if self.spec.component in (
            "number",
            "select",
            "switch",
        ):
            return EntityCategory.CONFIG

        return None

    @property
    def available(self):
        """Determine whether the discovered entity is currently available.

        Entities associated with legacy telemetry bindings are marked
        unavailable to avoid exposing duplicate measurements.

        Sensor and binary sensor entities also participate in
        measurement ownership resolution. Only the entity that owns
        a measurement identity may report itself as available.

        If neither condition prevents availability, the coordinator
        determines the current availability state.

        Returns:
            bool: True if the entity owns its measurement and the
            coordinator reports it as available; otherwise False.
        """
        if legacy_binding(self.spec) is not None:
            return False

        if self.spec.component in (
            "sensor",
            "binary_sensor",
        ):
            owner = self.coordinator.entity_claims.get(
                measurement_identity(self.spec),
                self.key,
            )

            if owner != self.key:
                return False

        return self.coordinator.available(self.key)

    @property
    def extra_state_attributes(self):
        """Provide additional diagnostic attributes for the entity.

        The attributes expose the MQTT state topic and indicate
        whether the entity is still present in the coordinator's
        active discovery specifications.

        Returns:
            dict: Additional entity attributes containing:
                - state_topic: MQTT topic supplying the entity state.
                - discovered: Whether the specification is currently known.
        """
        return {
            "state_topic": self.spec.state_topic,
            "discovered": self.key in self.coordinator.specs,
        }

    async def async_added_to_hass(self):
        """Register the entity for updates after it is added to Home Assistant.

        Call the parent lifecycle method and subscribe to coordinator
        notifications.

        The listener updates the entity state whenever the coordinator
        reports changed discovery data or telemetry values.

        The listener is automatically removed when Home Assistant
        removes the entity.
        """
        await super().async_added_to_hass()

        self.async_on_remove(self.coordinator.add_listener(self._update))

    @callback
    def _update(self):
        """Publish the current entity state to Home Assistant.

        This callback is invoked by the discovery coordinator when
        relevant telemetry or discovery information changes.

        It schedules the entity's current state and attributes
        to be written to Home Assistant's state machine.
        """
        self.async_write_ha_state()

    @property
    def value(self):
        """Return the latest raw MQTT value stored by the coordinator.

        The coordinator maintains the most recently received value
        for each discovery specification key.

        Returns:
            The current raw value, or None if no value is available.
        """
        return self.coordinator.values.get(self.key)


class DiscoverySensor(DiscoveryEntity, SensorEntity):
    """Represent a sensor created from a CCU MQTT discovery description.

    The sensor supports numeric measurements, timestamps, and
    unmodified values depending on its discovery configuration.
    """

    @property
    def native_value(self):
        """Return the sensor value in the format expected by Home Assistant.

        Measurements with a unit or state class are converted to
        floating-point numbers.

        Timestamp sensors convert their received string values into
        datetime objects.

        Other values are returned without modification.

        Returns:
            The numeric, datetime, or raw sensor value.
            Returns None if a numeric conversion fails.
        """
        value = self.value

        if value is not None and (self.native_unit_of_measurement or self.state_class):
            try:
                return float(value)
            except ValueError:
                return None

        if value is not None and self.device_class == SensorDeviceClass.TIMESTAMP:
            return dt_util.parse_datetime(value)

        return value

    @property
    def native_unit_of_measurement(self):
        """Return the measurement unit defined by MQTT discovery.

        Returns:
            str | None: Configured measurement unit, or None if
            the discovery specification does not define one.
        """
        return self.spec.config.get("unit_of_measurement")

    @property
    def device_class(self):
        """Return the Home Assistant sensor device class.

        The device class is read from the MQTT discovery configuration
        and validated against the supported Home Assistant classes.

        Returns:
            SensorDeviceClass | None: Valid sensor device class,
            or None if the configured value is unsupported.
        """
        value = self.spec.config.get("device_class")

        return SensorDeviceClass(value) if value in SensorDeviceClass else None

    @property
    def state_class(self):
        """Return the Home Assistant sensor state class.

        The state class describes how Home Assistant should interpret
        the measurement for statistics and long-term storage.

        Returns:
            SensorStateClass | None: Valid state class, or None
            if the discovery specification does not provide one.
        """
        value = self.spec.config.get("state_class")

        return SensorStateClass(value) if value in SensorStateClass else None


class DiscoveryBinarySensor(DiscoveryEntity, BinarySensorEntity):
    """Represent a binary sensor discovered through CCU MQTT.

    Binary sensors interpret configured MQTT payloads as active,
    inactive, or unknown states.
    """

    @property
    def device_class(self):
        """Return the binary sensor device class.

        The configured device class is validated against Home
        Assistant's supported binary sensor classes.

        Returns:
            BinarySensorDeviceClass | None: Valid device class,
            or None if no supported class is configured.
        """
        value = self.spec.config.get("device_class")

        return BinarySensorDeviceClass(value) if value in BinarySensorDeviceClass else None

    @property
    def is_on(self):
        """Determine the binary sensor state from its MQTT payload.

        Compare the current value with the configured payloads for
        active and inactive states.

        The default payloads are "ON" and "OFF" when no custom
        values are provided by MQTT discovery.

        Returns:
            bool | None: True for the active payload, False for
            the inactive payload, or None for an unknown value.
        """
        if self.value == str(self.spec.config.get("payload_on", "ON")):
            return True

        if self.value == str(self.spec.config.get("payload_off", "OFF")):
            return False

        return None


# Home Assistant supports asynchronous entity control methods.
# The synchronous abstract methods are intentionally not implemented.
# pylint: disable-next=abstract-method
class DiscoveryNumber(DiscoveryEntity, NumberEntity):
    """Represent a numeric CCU setting controlled through MQTT.

    The number entity exposes configurable minimum and maximum
    values, step size, and measurement units.

    Requested values are validated before being transmitted
    to the CCU.
    """

    @property
    def native_value(self):
        """Return the current numeric setting.

        Convert the raw MQTT value into a floating-point number.

        Returns:
            float | None: Current numeric value, or None if
            no value has been received.
        """
        return float(self.value) if self.value is not None else None

    @property
    def native_min_value(self):
        """Return the minimum value permitted by the CCU.

        Returns:
            float: Minimum value advertised through MQTT discovery.
        """
        return self.spec.config["min"]

    @property
    def native_max_value(self):
        """Return the maximum value permitted by the CCU.

        Returns:
            float: Maximum value advertised through MQTT discovery.
        """
        return self.spec.config["max"]

    @property
    def native_step(self):
        """Return the permitted increment for numeric values.

        The step size determines which values are valid between
        the configured minimum and maximum.

        Returns:
            float: Step size advertised through MQTT discovery.
        """
        return self.spec.config["step"]

    @property
    def native_unit_of_measurement(self):
        """Return the measurement unit of the numeric setting.

        Returns:
            str | None: Configured unit, or None if no unit
            is specified.
        """
        return self.spec.config.get("unit_of_measurement")

    async def async_set_native_value(self, value):
        """Validate and transmit a new numeric setting to the CCU.

        The requested value must be finite, remain within the
        advertised minimum and maximum, and match the configured
        step size.

        A small floating-point tolerance is used when validating
        step alignment.

        Valid values are forwarded to the discovery coordinator,
        which handles MQTT command transmission.

        Args:
            value: Numeric value requested by Home Assistant.

        Raises:
            HomeAssistantError: If the requested value is outside
                the permitted range or does not match the step size.
                The exception is created by mqtt_error().
        """
        if not math.isfinite(value) or not self.native_min_value <= value <= self.native_max_value:
            raise mqtt_error(
                "mqtt_value_out_of_range",
                "Requested value is outside the range advertised by the CCU",
            )

        steps = (value - self.native_min_value) / self.native_step

        if not math.isclose(
            steps,
            round(steps),
            abs_tol=1e-6,
        ):
            raise mqtt_error(
                "mqtt_invalid_step",
                "Requested value does not match the step advertised by the CCU",
            )

        await self.coordinator.async_write(
            self.key,
            value,
            str(value),
        )


# Home Assistant supports asynchronous entity control methods.
# The synchronous abstract methods are intentionally not implemented.
# pylint: disable-next=abstract-method
class DiscoverySelect(DiscoveryEntity, SelectEntity):
    """Represent a selectable CCU configuration option.

    Available options are supplied through MQTT discovery.
    Only advertised options may be sent to the CCU.
    """

    @property
    def options(self):
        """Return the list of selectable configuration options.

        Returns:
            list: Available options advertised by the CCU.
        """
        return list(self.spec.config["options"])

    @property
    def current_option(self):
        """Return the currently selected configuration option.

        The current MQTT value is considered valid only when it
        matches one of the advertised options.

        Returns:
            str | None: Current option, or None if the received
            value is not included in the available options.
        """
        return self.value if self.value in self.options else None

    async def async_select_option(self, option):
        """Validate and transmit a selected option to the CCU.

        Only values explicitly advertised through MQTT discovery
        are accepted.

        Args:
            option: Configuration option requested by Home Assistant.

        Raises:
            HomeAssistantError: If the requested option is not
                included in the advertised options.
                The exception is created by mqtt_error().
        """
        if option not in self.options:
            raise mqtt_error(
                "mqtt_invalid_option",
                "Requested option is not advertised by the CCU",
            )

        await self.coordinator.async_write(
            self.key,
            option,
            option,
        )


# Home Assistant supports asynchronous entity control methods.
# The synchronous abstract methods are intentionally not implemented.
# pylint: disable-next=abstract-method
class DiscoverySwitch(DiscoveryEntity, SwitchEntity):
    """Represent an MQTT-controlled CCU switch.

    The switch supports configurable command payloads and
    independent state payloads.

    This allows the CCU to use different values for commands
    and reported switch states.
    """

    @property
    def is_on(self):
        """Determine whether the switch is currently enabled.

        Compare the received MQTT value against the configured
        active and inactive state payloads.

        If dedicated state payloads are not defined, the command
        payloads are used as fallback values.

        Returns:
            bool | None: True when enabled, False when disabled,
            or None if the received state is unknown.
        """
        cfg = self.spec.config

        if self.value == str(
            cfg.get(
                "state_on",
                cfg.get("payload_on", "ON"),
            )
        ):
            return True

        if self.value == str(
            cfg.get(
                "state_off",
                cfg.get("payload_off", "OFF"),
            )
        ):
            return False

        return None

    async def async_turn_on(self, **kwargs):
        """Send the configured activation command to the CCU.

        Retrieve the activation payload from the discovery
        configuration and forward it to the coordinator.

        The corresponding expected state value is supplied
        separately because command and state payloads may differ.

        Args:
            **kwargs: Additional keyword arguments supplied by
                Home Assistant. Currently unused.
        """
        cfg = self.spec.config

        value = cfg.get(
            "payload_on",
            "ON",
        )

        await self.coordinator.async_write(
            self.key,
            value,
            str(cfg.get("state_on", value)),
        )

    async def async_turn_off(self, **kwargs):
        """Send the configured deactivation command to the CCU.

        Retrieve the deactivation payload from the discovery
        configuration and forward it to the coordinator.

        The corresponding expected state value is supplied
        separately because command and state payloads may differ.

        Args:
            **kwargs: Additional keyword arguments supplied by
                Home Assistant. Currently unused.
        """
        cfg = self.spec.config

        value = cfg.get(
            "payload_off",
            "OFF",
        )

        await self.coordinator.async_write(
            self.key,
            value,
            str(cfg.get("state_off", value)),
        )


# Map MQTT discovery component names to their corresponding
# Home Assistant entity implementations.
#
# This registry allows the discovery setup function to instantiate
# the appropriate entity class without platform-specific branching.
_ENTITY_TYPES = {
    "sensor": DiscoverySensor,
    "binary_sensor": DiscoveryBinarySensor,
    "number": DiscoveryNumber,
    "select": DiscoverySelect,
    "switch": DiscoverySwitch,
}


def setup_discovery_entities(
    hass,
    entry,
    async_add_entities,
    component,
):
    """Register MQTT discovery entities for a Home Assistant platform.

    Connect the requested platform to the shared MQTT discovery
    coordinator.

    Discovery specifications are processed through a callback,
    allowing entities to be created both during initial setup
    and when additional descriptions arrive later.

    Each discovery identity is added only once.

    Regular telemetry sensors remain managed by the integration's
    existing sensor factories. Native CCU energy counters are
    handled as a separate exception.

    The coordinator listener is registered for automatic cleanup
    when the configuration entry is unloaded.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry associated with the CCU device.
        async_add_entities: Home Assistant callback used to register
            newly created entities.
        component: Target Home Assistant platform, such as
            "sensor", "number", "select", or "switch".
    """
    coordinator = hass.data[DOMAIN][entry.entry_id][MQTT_DISCOVERY_COORDINATOR]

    # Track identities already created for this platform.
    # This prevents duplicate entities when discovery messages
    # are received repeatedly.
    added = set()

    @callback
    def add_specs(specs):
        """Create entities from newly received MQTT discovery specifications.

        Process discovery specifications in binding-priority order.

        Regular sensors and binary sensors remain handled by the
        integration's existing telemetry implementations.

        Previously generated duplicate discovery entities are
        disabled to preserve their registry entries and history.

        Native CCU energy counters are treated separately and
        registered using their dedicated entity implementation.

        For configuration and control platforms, entities are
        instantiated using the component-to-class registry.

        Newly created sensor entities are also registered with
        the integration's sensor catalog before being added
        to Home Assistant.

        Args:
            specs: Collection of MQTT discovery specifications
                received from the coordinator.
        """
        entities = []

        # Process specifications in priority order to ensure
        # consistent ownership and entity registration.
        for spec in sorted(specs, key=binding_priority):
            if component in ("sensor", "binary_sensor"):
                # Regular telemetry measurements are handled by
                # existing sensor factories.
                #
                # Previously generated discovery duplicates are
                # disabled without removing their registry history.
                #
                # Native CCU energy counters are the only exception.
                _disable_old_duplicate(
                    hass,
                    entry,
                    spec,
                )

                # Identify native CCU energy measurements and map
                # them to their corresponding logical energy roles.
                role = native_energy_key(spec)

                if role is not None:
                    # Store the discovery key associated with this
                    # native energy role for coordinator lookups.
                    coordinator.native_energy_bindings[role] = spec.key

                    # Create only one entity for each energy role,
                    # even when multiple discovery descriptions
                    # refer to the same measurement.
                    if role not in added:
                        added.add(role)

                        entity = CcuNativeEnergySensor(
                            coordinator,
                            role,
                            spec,
                        )

                        entities.append(entity)

                continue

            # Create control entities only once per discovery key.
            # Repeated discovery messages update coordinator data
            # without creating additional entity instances.
            if spec.key not in added:
                added.add(spec.key)

                entities.append(
                    _ENTITY_TYPES[component](
                        coordinator,
                        spec,
                    )
                )

        # Register newly created entities with Home Assistant.
        if entities:
            # Sensor entities are additionally registered with
            # the integration's internal sensor catalog.
            if component == "sensor":
                register_sensors(
                    hass,
                    entry,
                    entities,
                )

            async_add_entities(entities)

    # Register the platform callback with the discovery coordinator.
    #
    # Home Assistant automatically unregisters the callback
    # when the configuration entry is unloaded.
    entry.async_on_unload(
        coordinator.add_platform(
            component,
            add_specs,
        )
    )
