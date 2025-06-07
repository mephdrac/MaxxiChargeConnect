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


class BatteryPowerCharge(SensorEntity):
    def __init__(self, entry: ConfigEntry):
        self._unsub_dispatcher = None
        self._attr_suggested_display_precision = 2
        self._entry = entry
        self._attr_name = "Battery Power Charge"
        self._attr_unique_id = f"{entry.entry_id}_battery_power_charge"
        self._attr_icon = "mdi:battery-plus-variant"
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
        ccu = float(data.get("Pccu", 0))
        pv_power = float(data.get("PV_power_total", 0))
        batterie_leistung = round(pv_power - ccu, 3)

        if batterie_leistung >= 0:
            self._attr_native_value = batterie_leistung
            self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
