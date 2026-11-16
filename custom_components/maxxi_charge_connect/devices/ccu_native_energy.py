"""Expose native CCU energy counters alongside calculated energy sensors.

These entities report energy counters supplied directly by the CCU.
They remain separate from the existing Home Assistant integration sensors
that calculate energy from power readings.
"""

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import callback

from ..const import DOMAIN


class CcuNativeEnergySensor(SensorEntity):
    """Represent a native CCU energy counter with a stable entity identity.

    The counter role determines the unique ID and translation key. Its current
    discovery specification is resolved through the coordinator, allowing the
    source binding to change without changing the entity's identity.

    All supported source energy units are converted to kWh.
    """

    # Let Home Assistant compose the entity name from the device name and
    # the translated entity name.
    _attr_has_entity_name = True

    # Coordinator notifications provide updates, so polling is unnecessary.
    _attr_should_poll = False

    # Expose every native counter as an energy sensor measured in kWh.
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, role, spec):
        """Initialize the counter's identity and initial specification.

        Args:
            coordinator: Coordinator providing discovery specifications,
                counter bindings, current values, and update notifications.
            role: Stable logical role identifying the native energy counter.
            spec: Initial discovery specification, retained as a metadata
                fallback when no current binding is available.
        """
        self.coordinator = coordinator
        self.native_counter_role = role
        self._initial_spec = spec

        # Base the entity identity on the config entry and logical role,
        # independently of the currently bound MQTT source.
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{role}_ccu_counter"
        self._attr_translation_key = f"ccu_counter_{role}"

        # Battery PV energy roles contain a period and a zero-based index.
        # Reuse a shared translation key for each period and supply the
        # human-readable battery number through a translation placeholder.
        battery = re.fullmatch(r"battery_pv_energy_(today|total)_(\d+)", role)
        if battery:
            self._attr_translation_key = f"ccu_counter_battery_pv_energy_{battery[1]}"
            self._attr_translation_placeholders = {"index": str(int(battery[2]) + 1)}

        # Associate the entity with the device belonging to this config entry.
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.entry.entry_id)}}

    @property
    def spec(self):
        """Return the discovery specification currently bound to this role.

        Resolve the binding on every access so that coordinator changes are
        reflected without recreating the entity.

        Returns:
            The current specification, or None if the role has no binding
            or the bound specification is unavailable.
        """
        return self.coordinator.specs.get(self.coordinator.native_energy_bindings.get(self.native_counter_role))

    @property
    def native_value(self):
        """Return the current counter reading converted to kWh.

        Returns:
            The converted nonnegative reading, or None when the specification
            or reading is missing, or the converted value is negative or NaN.

        Raises:
            KeyError: If the specification has no unit_of_measurement entry
                or declares a unit other than Wh, kWh, or MWh.
            ValueError: If the reading is a string that cannot be converted
                to a float.
            TypeError: If the reading cannot be converted to a float.
        """
        spec = self.spec

        # Read a value only when a current source specification exists.
        value = self.coordinator.values.get(spec.key) if spec else None
        if value is None:
            return None

        # Normalize supported source units to the entity's fixed kWh unit.
        factor = {"Wh": 0.001, "kWh": 1, "MWh": 1000}[spec.config["unit_of_measurement"]]
        result = float(value) * factor

        # Reject negative readings. NaN also fails this comparison.
        return result if result >= 0 else None

    @property
    def available(self):
        """Return whether the bound source currently provides a valid reading.

        Availability requires a current specification, an available source
        according to the coordinator, and a usable converted counter value.
        """
        return self.spec is not None and self.coordinator.available(self.spec.key) and self.native_value is not None

    @property
    def state_class(self):
        """Return the source's supported energy state class.

        Use the current specification when available and otherwise consult
        the initial specification. Preserve total or total_increasing;
        default to total_increasing for missing or unsupported values.
        """
        spec = self.spec or self._initial_spec
        value = spec.config.get("state_class")
        return SensorStateClass(value) if value in ("total", "total_increasing") else SensorStateClass.TOTAL_INCREASING

    @property
    def extra_state_attributes(self):
        """Return metadata identifying the counter's origin and MQTT topic.

        Use the initial specification as a fallback so that source metadata
        remains available even when the current binding is missing.
        """
        spec = self.spec or self._initial_spec
        return {"source": "ccu", "state_topic": spec.state_topic}

    async def async_added_to_hass(self):
        """Subscribe to coordinator updates after the entity is added.

        Register the listener's unsubscribe callback with Home Assistant so
        the subscription is removed automatically when the entity is removed.
        """
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_listener(self._update))

    @callback
    def _update(self):
        """Write the current entity state after a coordinator notification.

        Home Assistant reevaluates the entity properties when writing the
        state, exposing the coordinator's latest values and metadata.
        """
        self.async_write_ha_state()
