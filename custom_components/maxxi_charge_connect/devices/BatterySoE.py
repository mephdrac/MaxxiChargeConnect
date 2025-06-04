from ..const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import EntityCategory
from homeassistant.const import CONF_WEBHOOK_ID

from homeassistant.const import UnitOfElectricCurrent, UnitOfEnergy, UnitOfPower

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)


class BatterySoE(SensorEntity):
    def __init__(self, entry: ConfigEntry):
        self._entry = entry
        self._attr_name = "Battery State of Energy"
        self._attr_unique_id = f"{entry.entry_id}_battery_soe"
        self._attr_icon = "mdi:file-document-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.BATTERY
        # self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        # self._attr_entity_category = EntityCategory.

    async def async_added_to_hass(self):
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_dispatcher:
            self._unsub_dispatcher()

    async def _handle_update(self, data):
        batteries_info = data.get("batteriesInfo")
        if (
            batteries_info
            and isinstance(batteries_info, list)
            and len(batteries_info) > 0
        ):
            battery_capacity = batteries_info[0].get("batteryCapacity")

        self._attr_native_value = battery_capacity
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "MaxxiChargeConnect (Community Integration)",
            "manufacturer": "mephdrac",
            "model": "Shows Information of MaxxiCharge",
            "entry_type": "service",
        }
