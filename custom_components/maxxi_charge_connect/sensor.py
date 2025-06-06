from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .devices.BatteryPower import BatteryPower
from .devices.BatterySensorManager import BatterySensorManager
from .devices.BatterySoc import BatterySoc
from .devices.BatterySoE import BatterySoE
from .devices.BatteryTodayEnergyCharge import BatteryTodayEnergyCharge
from .devices.BatteryTodayEnergyDischarge import BatteryTodayEnergyDischarge
from .devices.CcuEnergyToday import CcuEnergyToday
from .devices.CcuPower import CcuPower
from .devices.DeviceId import DeviceId
from .devices.FirmwareVersion import FirmwareVersion
from .devices.PowerMeter import PowerMeter
from .devices.PvPower import PvPower
from .devices.PvTodayEnergy import PvTodayEnergy
from .devices.PvTotalEnergy import PvTotalEnergy
from .devices.Rssi import Rssi
from .devices.WebhookId import WebhookId
from .http_scan.MaximumPower import MaximumPower
from .http_scan.MaxxiDataUpdateCoordinator import MaxxiDataUpdateCoordinator
from .http_scan.NumberOfBatteries import NumberOfBatteries
from .http_scan.OfflineOutputPower import OfflineOutputPower
from .http_scan.OutputOffset import OutputOffset
from .http_scan.PowerMeterIp import PowerMeterIp
from .http_scan.PowerMeterType import PowerMeterType

SENSOR_MANAGER = {}  # key: entry_id → value: BatterySensorManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    entry_id = entry.entry_id
    manager = BatterySensorManager(hass, entry, async_add_entities)
    SENSOR_MANAGER[entry_id] = manager
    await manager.setup()

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
    batteryTodayEnergyCharge = BatteryTodayEnergyCharge(entry)
    batteryTodayEnergyDischarge = BatteryTodayEnergyDischarge(entry)
    ccuEnergyToday = CcuEnergyToday(entry)
    webhookId = WebhookId(entry)

    coordinator = MaxxiDataUpdateCoordinator(hass, entry)

    powerMeterIp = PowerMeterIp(coordinator)
    powerMeterType = PowerMeterType(coordinator)
    maximumPower = MaximumPower(coordinator)
    offlineOutputPower = OfflineOutputPower(coordinator)
    numberOfBatteries = NumberOfBatteries(coordinator)
    outputOffset = OutputOffset(coordinator)

    async_add_entities(
        [
            sensor,
            rssiSensor,
            ccuPowerSensor,
            pvPowerSensor,
            batteryPowerSensor,
            batterySoc,
            powerMeter,
            firmwareVersion,
            pvTotalEnergy,
            pvTodayEnergy,
            batteryTodayEnergyCharge,
            batteryTodayEnergyDischarge,
            ccuEnergyToday,
            batterySoE,
            webhookId,
            powerMeterIp,
            powerMeterType,
            maximumPower,
            offlineOutputPower,
            numberOfBatteries,
            outputOffset,
        ]
    )
