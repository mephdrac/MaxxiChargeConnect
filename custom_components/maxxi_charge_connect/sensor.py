from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .devices.BatteryPower import BatteryPower
from .devices.BatterySoc import BatterySoc
from .devices.BatterySoE import BatterySoE
from .devices.CcuPower import CcuPower
from .devices.DeviceId import DeviceId
from .devices.FirmwareVersion import FirmwareVersion
from .devices.PowerMeter import PowerMeter
from .devices.PvPower import PvPower
from .devices.PvTotalEnergy import PvTotalEnergy
from .devices.Rssi import Rssi
from .devices.PvTodayEnergy import PvTodayEnergy


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
    pvTotalEnergy = PvTotalEnergy(entry)
    pvTodayEnergy = PvTodayEnergy(entry)

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
            pvTotalEnergy,
            pvTodayEnergy,
        ]
    )
