from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .devices.BatteryPowerCharge import BatteryPowerCharge
from .devices.BatteryPowerDischarge import BatteryPowerDischarge
from .devices.BatterySensorManager import BatterySensorManager
from .devices.BatterySoc import BatterySoc
from .devices.BatterySoE import BatterySoE
from .devices.BatteryTodayEnergyCharge import BatteryTodayEnergyCharge
from .devices.BatteryTodayEnergyDischarge import BatteryTodayEnergyDischarge
from .devices.BatteryTotalEnergyCharge import BatteryTotalEnergyCharge
from .devices.BatteryTotalEnergyDischarge import BatteryTotalEnergyDischarge
from .devices.CcuEnergyToday import CcuEnergyToday
from .devices.CcuTotalEnergy import CcuTotalEnergy
from .devices.CcuPower import CcuPower

from .devices.DeviceId import DeviceId
from .devices.FirmwareVersion import FirmwareVersion
from .devices.PowerMeter import PowerMeter
from .devices.PvPower import PvPower
from .devices.PvTodayEnergy import PvTodayEnergy
from .devices.PvTotalEnergy import PvTotalEnergy
from .devices.Rssi import Rssi
from .devices.WebhookId import WebhookId
from .devices.BatteryPower import BatteryPower
from .devices.PowerConsumption import PowerConsumption

import asyncio

SENSOR_MANAGER = {}  # key: entry_id → value: BatterySensorManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    manager = BatterySensorManager(hass, entry, async_add_entities)
    SENSOR_MANAGER[entry.entry_id] = manager
    await manager.setup()

    sensor = DeviceId(entry)
    rssiSensor = Rssi(entry)
    ccuPower = CcuPower(entry)
    pvPowerSensor = PvPower(entry)
    batteryPowerCharge = BatteryPowerCharge(entry)
    batteryPowerDischarge = BatteryPowerDischarge(entry)
    batterySoc = BatterySoc(entry)
    batterySoE = BatterySoE(entry)
    powerMeter = PowerMeter(entry)
    firmwareVersion = FirmwareVersion(entry)
    webhookId = WebhookId(entry)
    batteryPower = BatteryPower(entry)
    powerConsumption = PowerConsumption(entry)

    async_add_entities(
        [
            sensor,
            rssiSensor,
            ccuPower,
            pvPowerSensor,
            batteryPowerCharge,
            batteryPowerDischarge,
            batterySoc,
            batteryPower,
            powerMeter,
            firmwareVersion,
            batterySoE,
            webhookId,
            powerConsumption
        ]
    )
    await asyncio.sleep(0)

    pvTodayEnergy = PvTodayEnergy(entry, pvPowerSensor.entity_id)
    pvTotalEnergy = PvTotalEnergy(entry, pvPowerSensor.entity_id)
    ccuEnergyToday = CcuEnergyToday(entry, ccuPower.entity_id)
    ccuEnergyTotal = CcuTotalEnergy(entry, ccuPower.entity_id)
    batteryTodayEnergyCharge = BatteryTodayEnergyCharge(
        entry, batteryPowerCharge.entity_id
    )
    batteryTodayEnergyDischarge = BatteryTodayEnergyDischarge(
        entry, batteryPowerDischarge.entity_id
    )

    batteryTotalEnergyCharge = BatteryTotalEnergyCharge(
        entry, batteryPowerCharge.entity_id
    )
    batteryTotalEnergyDischarge = BatteryTotalEnergyDischarge(
        entry, batteryPowerDischarge.entity_id
    )

    async_add_entities(
        [
            pvTodayEnergy,
            pvTotalEnergy,
            ccuEnergyToday,
            ccuEnergyTotal,
            batteryTodayEnergyCharge,
            batteryTodayEnergyDischarge,
            batteryTotalEnergyCharge,
            batteryTotalEnergyDischarge,
        ]
    )
