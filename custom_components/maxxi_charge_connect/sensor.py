import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .devices.DeviceId import DeviceId
from .devices.Rssi import Rssi
from .devices.CcuPower import CcuPower
from .devices.PvPower import PvPower
from .devices.BatteryPower import BatteryPower



_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    sensor = DeviceId(entry)
    rssiSensor = Rssi(entry)
    ccuPowerSensor = CcuPower(entry)
    pvPowerSensor = PvPower(entry)
    batteryPowerSensor = BatteryPower(entry)
    hello_sensor = HelloWorldSensor(entry)
    async_add_entities([sensor, rssiSensor, ccuPowerSensor, pvPowerSensor, batteryPowerSensor, hello_sensor])


class HelloWorldSensor(SensorEntity):
    def __init__(self, entry: ConfigEntry):
        self._attr_name = entry.data.get("name", "Hello Sensor")
        self._attr_unique_id = f"{entry.entry_id}_sensor"
        self._entry = entry
        self._state = "Bereit"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        self._state = "Aktualisiert"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "MaxxiChargeConnect",
            "manufacturer": "Maxxi GmbH",
            "model": "Maxxicharge",
        }
