"""Home Assistant entities backed by CCU-provided MQTT discovery descriptions."""

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
    digest = hashlib.sha256(spec.key.encode()).hexdigest()[:24]
    return f"{entry_id}_mqtt_discovery_{digest}"


def _disable_old_duplicate(hass, entry, spec, *, duplicate=True):
    """Preserve history while retiring only our previously generated duplicate."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(spec.component, DOMAIN, _unique_id(entry.entry_id, spec))
    if entity_id is None:
        return
    entity = registry.async_get(entity_id)
    if entity is None or entity.config_entry_id != entry.entry_id:
        return
    if duplicate and entity.disabled_by is None:
        registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
    elif not duplicate and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
        registry.async_update_entity(entity_id, disabled_by=None)


class DiscoveryEntity(Entity):
    """Share identity, metadata and lifecycle for all discovered platforms."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, spec) -> None:
        self.coordinator = coordinator
        self._initial_spec = spec
        self.key = spec.key
        self._attr_unique_id = _unique_id(coordinator.entry.entry_id, spec)
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.entry.entry_id)}}
        key = _CONTROL_TRANSLATIONS.get((spec.component, spec.name.casefold().strip()))
        if key is not None:
            self._attr_translation_key = key

    @property
    def spec(self):
        return self.coordinator.specs.get(self.key, self._initial_spec)

    @property
    def name(self):
        if (
            self.platform is not None
            and (self.spec.component, self.spec.name.casefold().strip()) in _CONTROL_TRANSLATIONS
        ):
            return super().name
        return self.spec.name

    @property
    def entity_category(self):
        category = self.spec.config.get("entity_category")
        if category in (EntityCategory.CONFIG, EntityCategory.DIAGNOSTIC):
            return EntityCategory(category)
        if self.spec.component in ("number", "select", "switch"):
            return EntityCategory.CONFIG
        return None

    @property
    def available(self):
        if legacy_binding(self.spec) is not None:
            return False
        if self.spec.component in ("sensor", "binary_sensor"):
            owner = self.coordinator.entity_claims.get(measurement_identity(self.spec), self.key)
            if owner != self.key:
                return False
        return self.coordinator.available(self.key)

    @property
    def extra_state_attributes(self):
        return {"state_topic": self.spec.state_topic, "discovered": self.key in self.coordinator.specs}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_listener(self._update))

    @callback
    def _update(self):
        self.async_write_ha_state()

    @property
    def value(self):
        return self.coordinator.values.get(self.key)


class DiscoverySensor(DiscoveryEntity, SensorEntity):
    @property
    def native_value(self):
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
        return self.spec.config.get("unit_of_measurement")

    @property
    def device_class(self):
        value = self.spec.config.get("device_class")
        return SensorDeviceClass(value) if value in SensorDeviceClass else None

    @property
    def state_class(self):
        value = self.spec.config.get("state_class")
        return SensorStateClass(value) if value in SensorStateClass else None


class DiscoveryBinarySensor(DiscoveryEntity, BinarySensorEntity):
    @property
    def device_class(self):
        value = self.spec.config.get("device_class")
        return BinarySensorDeviceClass(value) if value in BinarySensorDeviceClass else None

    @property
    def is_on(self):
        if self.value == str(self.spec.config.get("payload_on", "ON")):
            return True
        if self.value == str(self.spec.config.get("payload_off", "OFF")):
            return False
        return None


class DiscoveryNumber(DiscoveryEntity, NumberEntity):
    @property
    def native_value(self):
        return float(self.value) if self.value is not None else None

    @property
    def native_min_value(self):
        return self.spec.config["min"]

    @property
    def native_max_value(self):
        return self.spec.config["max"]

    @property
    def native_step(self):
        return self.spec.config["step"]

    @property
    def native_unit_of_measurement(self):
        return self.spec.config.get("unit_of_measurement")

    async def async_set_native_value(self, value):
        if not math.isfinite(value) or not self.native_min_value <= value <= self.native_max_value:
            raise mqtt_error("mqtt_value_out_of_range", "Requested value is outside the range advertised by the CCU")
        steps = (value - self.native_min_value) / self.native_step
        if not math.isclose(steps, round(steps), abs_tol=1e-6):
            raise mqtt_error("mqtt_invalid_step", "Requested value does not match the step advertised by the CCU")
        await self.coordinator.async_write(self.key, value, str(value))


class DiscoverySelect(DiscoveryEntity, SelectEntity):
    @property
    def options(self):
        return list(self.spec.config["options"])

    @property
    def current_option(self):
        return self.value if self.value in self.options else None

    async def async_select_option(self, option):
        if option not in self.options:
            raise mqtt_error("mqtt_invalid_option", "Requested option is not advertised by the CCU")
        await self.coordinator.async_write(self.key, option, option)


class DiscoverySwitch(DiscoveryEntity, SwitchEntity):
    @property
    def is_on(self):
        cfg = self.spec.config
        if self.value == str(cfg.get("state_on", cfg.get("payload_on", "ON"))):
            return True
        if self.value == str(cfg.get("state_off", cfg.get("payload_off", "OFF"))):
            return False
        return None

    async def async_turn_on(self, **kwargs):
        cfg = self.spec.config
        value = cfg.get("payload_on", "ON")
        await self.coordinator.async_write(self.key, value, str(cfg.get("state_on", value)))

    async def async_turn_off(self, **kwargs):
        cfg = self.spec.config
        value = cfg.get("payload_off", "OFF")
        await self.coordinator.async_write(self.key, value, str(cfg.get("state_off", value)))


_ENTITY_TYPES = {
    "sensor": DiscoverySensor,
    "binary_sensor": DiscoveryBinarySensor,
    "number": DiscoveryNumber,
    "select": DiscoverySelect,
    "switch": DiscoverySwitch,
}


def setup_discovery_entities(hass, entry, async_add_entities, component):
    """Add each stable discovery identity once, including descriptions received later."""
    coordinator = hass.data[DOMAIN][entry.entry_id][MQTT_DISCOVERY_COORDINATOR]
    added = set()

    @callback
    def add_specs(specs):
        entities = []
        for spec in sorted(specs, key=binding_priority):
            if component in ("sensor", "binary_sensor"):
                # Readings always use our existing factories. Native CCU energy
                # counters are the explicitly requested, separate exception.
                _disable_old_duplicate(hass, entry, spec)
                role = native_energy_key(spec)
                if role is not None:
                    coordinator.native_energy_bindings[role] = spec.key
                    if role not in added:
                        added.add(role)
                        entity = CcuNativeEnergySensor(coordinator, role, spec)
                        entities.append(entity)
                continue
            if spec.key not in added:
                added.add(spec.key)
                entities.append(_ENTITY_TYPES[component](coordinator, spec))
        if entities:
            if component == "sensor":
                register_sensors(hass, entry, entities)
            async_add_entities(entities)

    entry.async_on_unload(coordinator.add_platform(component, add_specs))
