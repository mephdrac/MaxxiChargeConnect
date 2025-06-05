from datetime import UTC, datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_change

from ..const import DOMAIN


class BatteryTodayEnergyDischarge(RestoreSensor):
    def __init__(self, entry):
        self._entry = entry
        self._attr_name = "Battery Discharge Today"
        self._attr_unique_id = f"{entry.entry_id}_battery_energy_discharge_today"
        self._attr_icon = "mdi:battery-minus-outline"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_native_value = None
        self._last_update = None
        self._energy_kwh = 0.0
        self._unsub_dispatcher = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable", None):
            try:
                self._energy_kwh = float(last_state.state)
            except ValueError:
                self._energy_kwh = 0.0

        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )
        # self.async_on_remove(self._unsub_dispatcher)

        async_track_time_change(
            self.hass,
            self._reset_energy_daily,
            hour=0,
            minute=0,
            second=0,
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        try:
            ccu = float(data.get("Pccu", 0))
            pv_power = float(data.get("PV_power_total", 0))
            batterie_leistung = round(pv_power - ccu, 3)
        except (TypeError, ValueError):
            return

        now = datetime.now(UTC)
        if self._last_update:
            delta = (now - self._last_update).total_seconds()
            if 0 < delta < 300:
                if batterie_leistung <= 0:
                    self._energy_kwh += (-1 * batterie_leistung * delta) / 3_600_000

        self._last_update = now
        self._attr_native_value = round(self._energy_kwh, 3)
        self.async_write_ha_state()

    async def _reset_energy_daily(self, now):
        self._energy_kwh = 0.0
        self._last_update = None
        self._attr_native_value = 0.0
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
