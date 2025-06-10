from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
from homeassistant.helpers.dispatcher import async_dispatcher_connect


class BatterySoE(SensorEntity):
    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatterySoE"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        self._attr_suggested_display_precision = 2
        self._unsub_dispatcher = None
        self._entry = entry
        # self._attr_name = "Battery State of Energy"
        self._attr_unique_id = f"{entry.entry_id}_battery_soe"
        self._attr_icon = "mdi:home-battery"
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

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
        batteries_info = data.get("batteriesInfo")
        if (
            batteries_info
            and isinstance(batteries_info, list)
            and len(batteries_info) > 0
        ):
            batteries_info = data.get("batteriesInfo", [])
            total_capacity = sum(
                battery.get("batteryCapacity", 0) for battery in batteries_info
            )

        self._attr_native_value = total_capacity
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
