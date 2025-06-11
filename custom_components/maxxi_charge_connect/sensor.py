"""Dieses Modul initialisiert und registriert die Sensor-Entitäten für die MaxxiChargeConnect-Integration in Home Assistant.

Es verwaltet die Sensoren über den BatterySensorManager pro ConfigEntry und fügt alle relevanten Sensoren
beim Setup hinzu. Sensoren umfassen unter anderem Geräte-ID, Batteriestatus, PV-Leistung, Netzbezug/-einspeisung
und zugehörige Energie-Statistiken.

Module-Level Variable:
    SENSOR_MANAGER (dict): Verwaltung der BatterySensorManager Instanzen, keyed nach entry_id.

"""

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .devices.BatteryPower import BatteryPower
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
from .devices.CcuEnergyTotal import CcuEnergyTotal
from .devices.CcuPower import CcuPower
from .devices.DeviceId import DeviceId
from .devices.FirmwareVersion import FirmwareVersion
from .devices.GridExport import GridExport
from .devices.GridExportEnergyToday import GridExportEnergyToday
from .devices.GridExportEnergyTotal import GridExportEnergyTotal
from .devices.GridImport import GridImport
from .devices.GridImportEnergyToday import GridImportEnergyToday
from .devices.GridImportEnergyTotal import GridImportEnergyTotal
from .devices.PowerConsumption import PowerConsumption
from .devices.PowerMeter import PowerMeter
from .devices.PvPower import PvPower
from .devices.PvSelfConsumption import PvSelfConsumption
from .devices.PvSelfConsumptionEnergyToday import PvSelfConsumptionEnergyToday
from .devices.PvSelfConsumptionEnergyTotal import PvSelfConsumptionEnergyTotal
from .devices.PvTodayEnergy import PvTodayEnergy
from .devices.PvTotalEnergy import PvTotalEnergy
from .devices.Rssi import Rssi
from .devices.WebhookId import WebhookId

SENSOR_MANAGER = {}  # key: entry_id → value: BatterySensorManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Setzt die Sensoren für einen ConfigEntry asynchron auf.

    Erstellt eine BatterySensorManager-Instanz, die die Verwaltung der Batteriesensoren übernimmt.
    Fügt eine Vielzahl von Sensor-Objekten hinzu, die verschiedene Datenpunkte der Hardware abbilden,
    darunter Batterieladung, Entladung, SOC, SoE, PV-Leistung, Netzverbrauch und mehr.

    Args:
        hass (HomeAssistant): Die Home Assistant Instanz.
        entry (ConfigEntry): Die Konfigurationseintrag, für den die Sensoren erstellt werden.
        async_add_entities (AddEntitiesCallback): Callback-Funktion zum Hinzufügen von Entities in HA.

    Returns:
        None

    """

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
    gridExport = GridExport(entry)
    gridImport = GridImport(entry)
    pvSelfConsumption = PvSelfConsumption(entry)

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
            powerConsumption,
            gridExport,
            gridImport,
            pvSelfConsumption,
        ]
    )
    await asyncio.sleep(0)

    pvTodayEnergy = PvTodayEnergy(hass, entry, pvPowerSensor.entity_id)
    pvTotalEnergy = PvTotalEnergy(hass, entry, pvPowerSensor.entity_id)
    ccuEnergyToday = CcuEnergyToday(hass, entry, ccuPower.entity_id)
    ccuEnergyTotal = CcuEnergyTotal(hass, entry, ccuPower.entity_id)
    batteryTodayEnergyCharge = BatteryTodayEnergyCharge(
        hass, entry, batteryPowerCharge.entity_id
    )
    batteryTodayEnergyDischarge = BatteryTodayEnergyDischarge(
        hass, entry, batteryPowerDischarge.entity_id
    )

    batteryTotalEnergyCharge = BatteryTotalEnergyCharge(
        hass, entry, batteryPowerCharge.entity_id
    )
    batteryTotalEnergyDischarge = BatteryTotalEnergyDischarge(
        hass, entry, batteryPowerDischarge.entity_id
    )

    gridExportEnergyToday = GridExportEnergyToday(hass, entry, gridExport.entity_id)
    gridExportEnergyTotal = GridExportEnergyTotal(hass, entry, gridExport.entity_id)

    gridImportEnergyToday = GridImportEnergyToday(hass, entry, gridImport.entity_id)
    gridImportEnergyTotal = GridImportEnergyTotal(hass, entry, gridImport.entity_id)

    pvSelfConsumptionToday = PvSelfConsumptionEnergyToday(
        hass, entry, pvSelfConsumption.entity_id
    )
    pvSelfConsumptionTotal = PvSelfConsumptionEnergyTotal(
        hass, entry, pvSelfConsumption.entity_id
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
            gridExportEnergyToday,
            gridExportEnergyTotal,
            gridImportEnergyToday,
            gridImportEnergyTotal,
            pvSelfConsumptionToday,
            pvSelfConsumptionTotal,
        ]
    )
