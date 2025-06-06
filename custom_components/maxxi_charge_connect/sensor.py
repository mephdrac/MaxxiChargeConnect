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
from .http_scan.MaxxiDataUpdateCoordinator import MaxxiDataUpdateCoordinator
from .http_scan.HttpScanTextClass import HttpScanTextClass

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

    sensorList = []
    sensorList.append(("PowerMeterIp", "Messgerät IP:"))
    sensorList.append(("PowerMeterType", "Messgerät Typ:"))
    sensorList.append(("MaximumPower", "Maximale Leistung:"))
    sensorList.append(("OfflineOutputPower", "Offline-Ausgangsleistung:"))
    sensorList.append(("NumberOfBatteries", "Batterien im System:"))
    sensorList.append(("OutputOffset", "Ausgabe korrigieren:"))
    sensorList.append(("CcuSpeed", "CCU-Geschwindigkeit:"))

    coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensorList)

    powerMeterIp = HttpScanTextClass(
        coordinator, "PowerMeterIp", "Power Meter IP", "mdi:ip"
    )
    powerMeterType = HttpScanTextClass(
        coordinator, "PowerMeterType(", "Power Meter Type", "mdi:chip"
    )
    maximumPower = HttpScanTextClass(
        coordinator, "MaximumPower", "Maximum Power", "mdi:flash"
    )
    offlineOutputPower = HttpScanTextClass(
        coordinator, "OfflineOutputPower", "Offline Output Power", "mdi:flash"
    )
    numberOfBatteries = HttpScanTextClass(
        coordinator, "NumberOfBatteries", "Number of Batteries", "mdi:layers"
    )
    outputOffset = HttpScanTextClass(
        coordinator, "OutputOffset", "Output Offset", "mdi:flash"
    )
    ccuSpeed = HttpScanTextClass(coordinator, "CcuSpeed", "CCU - Speed", "mdi:flash")

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
            ccuSpeed,
        ]
    )
