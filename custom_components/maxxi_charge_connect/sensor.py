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
from .devices.BatterySoc import BatterySoc
from .devices.BatterySoE import BatterySoE
from .devices.PowerMeter import PowerMeter
from .devices.FirmwareVersion import FirmwareVersion


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    sensor = DeviceId(entry)
    rssiSensor = Rssi(entry)
    ccuPowerSensor = CcuPower(entry)
    pvPowerSensor = PvPower(entry)
    batteryPowerSensor = BatteryPower(entry)
    batterySoc = BatterySoc(entry)
    batterySoE = BatterySoE(entry)
    powerMeter = PowerMeter(entry)
    firmwareVersion = FirmwareVersion(entry)

    async_add_entities(
        [
            sensor,
            rssiSensor,
            ccuPowerSensor,
            pvPowerSensor,
            batteryPowerSensor,
            batterySoc,
            batterySoE,
            powerMeter,
            firmwareVersion,
        ]
    )
