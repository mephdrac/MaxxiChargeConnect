from datetime import timedelta
import logging

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from .translationsForIntegrationSensors import get_localized_name

_LOGGER = logging.getLogger(__name__)


class GridExportEnergyToday(IntegrationSensor):
    def __init__(self, hass, entry, source_entity_id: str):
        super().__init__(
            source_entity=source_entity_id,
            # name="Grid Export Energy Today",
            name=get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_grid_export_energy_today",
            integration_method="trapezoidal",
            round_digits=3,
            unit_prefix="k",
            unit_time=UnitOfTime.HOURS,
            max_sub_interval=timedelta(seconds=120),
        )
        self._unsub_time_reset = None
        self._entry = entry
        self._attr_icon = "mdi:counter"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        # Setze initialen Reset-Zeitpunkt auf heutige Mitternacht lokal
        local_midnight = dt_util.start_of_local_day()
        self._last_reset = dt_util.as_utc(local_midnight)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Registriere täglichen Reset um 0:00 Uhr lokale Zeit
        self._unsub_time_reset = async_track_time_change(
            self.hass,
            self._reset_energy_daily,
            hour=0,
            minute=0,
            second=0,
        )

        if self._unsub_time_reset is not None:
            self.async_on_remove(self._unsub_time_reset)

    async def _reset_energy_daily(self, now):
        _LOGGER.warning("resetting daily energy at %s", now)

        # Setze Reset-Zeitpunkt auf aktuelle Mitternacht lokal (als UTC)
        local_midnight = dt_util.start_of_local_day()
        self._last_reset = dt_util.as_utc(local_midnight)

        try:
            self._integration.reset()
            _LOGGER.warning("internal integration reset")
        except Exception as e:
            _LOGGER.error("reset failed – %s", e)

        await self.async_write_ha_state()

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
