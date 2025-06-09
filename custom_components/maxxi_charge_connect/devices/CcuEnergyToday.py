from datetime import timedelta

from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .translationsForIntegrationSensors import get_localized_name


class CcuEnergyToday(IntegrationSensor):
    def __init__(self, hass, entry, source_entity_id: str):
        super().__init__(
            source_entity=source_entity_id,
            # name="CCU Energy Today",
            name=get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_CcuEnergyToday",
            integration_method="trapezoidal",
            round_digits=3,
            unit_prefix="k",
            unit_time="h",
            max_sub_interval=timedelta(seconds=300),
        )
        self._unsub_time_reset = None
        self._entry = entry
        self._attr_icon = "mdi:counter"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._last_reset = dt_util.utcnow()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        async_track_time_change(
            self.hass,
            self._reset_energy_daily,
            hour=0,
            minute=0,
            second=0,
        )
        if self._unsub_time_reset is not None:
            self.async_on_remove(self._unsub_time_reset)

    async def _reset_energy_daily(self, now):
        self._last_reset = dt_util.utcnow()
        self._integration.reset()
        self.async_write_ha_state()

    @property
    def last_reset(self):
        return self._last_reset

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
