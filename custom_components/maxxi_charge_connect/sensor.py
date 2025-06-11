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

from .devices.battery_power import BatteryPower
from .devices.battery_power_charge import BatteryPowerCharge
from .devices.battery_power_discharge import BatteryPowerDischarge
from .devices.battery_sensor_manager import BatterySensorManager
from .devices.battery_soc import BatterySoc
from .devices.battery_soe import BatterySoE
from .devices.battery_today_energy_charge import BatteryTodayEnergyCharge
from .devices.battery_today_energy_discharge import BatteryTodayEnergyDischarge
from .devices.battery_total_energy_charge import BatteryTotalEnergyCharge
from .devices.battery_total_energy_discharge import BatteryTotalEnergyDischarge
from .devices.ccu_energy_today import CcuEnergyToday
from .devices.ccu_energy_total import CcuEnergyTotal
from .devices.ccu_power import CcuPower
from .devices.device_id import DeviceId
from .devices.firmware_version import FirmwareVersion
from .devices.grid_export import GridExport
from .devices.grid_export_energy_today import GridExportEnergyToday
from .devices.grid_export_energy_total import GridExportEnergyTotal
from .devices.grid_import import GridImport
from .devices.grid_import_energy_today import GridImportEnergyToday
from .devices.grid_import_energy_total import GridImportEnergyTotal
from .devices.power_consumption import PowerConsumption
from .devices.power_meter import PowerMeter
from .devices.pv_power import PvPower
from .devices.pv_self_consumption import PvSelfConsumption
from .devices.pv_self_consumption_energy_today import PvSelfConsumptionEnergyToday
from .devices.pv_self_consumption_energy_total import PvSelfConsumptionEnergyTotal
from .devices.pv_today_energy import PvTodayEnergy
from .devices.pv_total_energy import PvTotalEnergy
from .devices.rssi import Rssi
from .devices.webhook_id import WebhookId

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
