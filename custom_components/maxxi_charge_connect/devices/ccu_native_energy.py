"""Additional native CCU counters alongside the existing calculated energy sensors."""

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import callback

from ..const import DOMAIN


class CcuNativeEnergySensor(SensorEntity):
    """One stable, explicitly named CCU counter; never replaces an HA integral."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, role, spec):
        self.coordinator = coordinator
        self.native_counter_role = role
        self._initial_spec = spec
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{role}_ccu_counter"
        self._attr_translation_key = f"ccu_counter_{role}"
        battery = re.fullmatch(r"battery_pv_energy_(today|total)_(\d+)", role)
        if battery:
            self._attr_translation_key = f"ccu_counter_battery_pv_energy_{battery[1]}"
            self._attr_translation_placeholders = {"index": str(int(battery[2]) + 1)}
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.entry.entry_id)}}

    @property
    def spec(self):
        return self.coordinator.specs.get(self.coordinator.native_energy_bindings.get(self.native_counter_role))

    @property
    def native_value(self):
        spec = self.spec
        value = self.coordinator.values.get(spec.key) if spec else None
        if value is None:
            return None
        factor = {"Wh": 0.001, "kWh": 1, "MWh": 1000}[spec.config["unit_of_measurement"]]
        result = float(value) * factor
        return result if result >= 0 else None

    @property
    def available(self):
        return self.spec is not None and self.coordinator.available(self.spec.key) and self.native_value is not None

    @property
    def state_class(self):
        spec = self.spec or self._initial_spec
        value = spec.config.get("state_class")
        return SensorStateClass(value) if value in ("total", "total_increasing") else SensorStateClass.TOTAL_INCREASING

    @property
    def extra_state_attributes(self):
        spec = self.spec or self._initial_spec
        return {"source": "ccu", "state_topic": spec.state_topic}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_listener(self._update))

    @callback
    def _update(self):
        self.async_write_ha_state()
