from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.helpers.dispatcher import async_dispatcher_connect


class PvSelfConsumption(SensorEntity):
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "PvSelfConsumption"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        self._unsub_dispatcher = None
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "PV Self-Consumption"
        self._attr_unique_id = f"{entry.entry_id}_pv_consumption"
        self._attr_icon = "mdi:solar-power-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def async_added_to_hass(self):
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        # PV-Eigenverbrauch
        pv_power = float(data.get("PV_power_total", 0))
        pr = float(data.get("Pr", 0))
        self._attr_native_value = pv_power - max(-pr, 0)
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
