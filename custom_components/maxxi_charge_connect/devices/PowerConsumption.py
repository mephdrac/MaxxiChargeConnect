from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.tools import isPccuOk, isPrOk

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.helpers.dispatcher import async_dispatcher_connect


class PowerConsumption(SensorEntity):
    _attr_translation_key = "PowerConsumption"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        self._unsub_dispatcher = None
        self._entry = entry
        self._attr_suggested_display_precision = 2
        # self._attr_name = "House Consumption"
        self._attr_unique_id = f"{entry.entry_id}_power_consumption"
        self._attr_icon = "mdi:home-import-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        # self._attr_entity_category = EntityCategory.

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
        # Verbrauch = Pccu + Pr
        pccu = float(data.get("Pccu", 0))

        if isPccuOk(pccu):
            pr = float(data.get("Pr", 0))
            if isPrOk(pr):
                self._attr_native_value = round(pccu + max(-pr, 0), 2)
                self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
