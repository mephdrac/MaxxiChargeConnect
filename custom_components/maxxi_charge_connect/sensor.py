"""Dieses Modul initialisiert und registriert die Sensor-Entitäten für die
MaxxiChargeConnect-Integration in Home Assistant.

Es verwaltet die Sensoren über den BatterySensorManager pro ConfigEntry
und fügt alle relevanten Sensoren
beim Setup hinzu. Sensoren umfassen unter anderem Geräte-ID, Batteriestatus,
PV-Leistung, Netzbezug/-einspeisung
und zugehörige Energie-Statistiken.

Module-Level Variable:
    SENSOR_MANAGER (dict): Verwaltung der BatterySensorManager Instanzen, keyed nach entry_id.

"""

import asyncio
import logging

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

# from .devices.power_consumption import PowerConsumption
from .devices.power_meter import PowerMeter
from .devices.pv_power import PvPower

# from .devices.pv_self_consumption import PvSelfConsumption
# from .devices.pv_self_consumption_energy_today import PvSelfConsumptionEnergyToday
# from .devices.pv_self_consumption_energy_total import PvSelfConsumptionEnergyTotal
from .devices.pv_today_energy import PvTodayEnergy
from .devices.pv_total_energy import PvTotalEnergy
from .devices.rssi import Rssi
from .devices.webhook_id import WebhookId

from .http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator
from .http_scan.http_scan_text import HttpScanText

SENSOR_MANAGER = {}  # key: entry_id → value: BatterySensorManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(  # pylint: disable=too-many-locals, too-many-statements
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Setzt die Sensoren für einen ConfigEntry asynchron auf.

    Erstellt eine BatterySensorManager-Instanz, die die Verwaltung der Batteriesensoren übernimmt.
    Fügt eine Vielzahl von Sensor-Objekten hinzu, die verschiedene Datenpunkte der
    Hardware abbilden, darunter Batterieladung, Entladung, SOC, SoE, PV-Leistung, Netzverbrauch
    und mehr.

    Args:
        hass (HomeAssistant): Die Home Assistant Instanz.
        entry (ConfigEntry): Die Konfigurationseintrag, für den die Sensoren erstellt werden.
        async_add_entities (AddEntitiesCallback): Callback-Funktion zum Hinzufügen von
          Entities in HA.

    Returns:
        None

    """

    manager = BatterySensorManager(hass, entry, async_add_entities)
    SENSOR_MANAGER[entry.entry_id] = manager
    await manager.setup()

    sensor = DeviceId(entry)
    rssi_sensor = Rssi(entry)
    ccu_power = CcuPower(entry)
    pv_power_sensor = PvPower(entry)
    battery_power_charge = BatteryPowerCharge(entry)
    battery_power_discharge = BatteryPowerDischarge(entry)
    battery_soc = BatterySoc(entry)
    battery_soe = BatterySoE(entry)
    power_meter = PowerMeter(entry)
    firmware_version = FirmwareVersion(entry)
    webhook_id = WebhookId(entry)
    battery_power = BatteryPower(entry)
    # power_consumption = PowerConsumption(entry)
    grid_export = GridExport(entry)
    grid_import = GridImport(entry)
    # pv_self_consumption = PvSelfConsumption(entry)

    sensor_list = []
    sensor_list.append(("PowerMeterIp", "Messgerät IP:"))
    sensor_list.append(("PowerMeterType", "Messgerät Typ:"))
    sensor_list.append(("MaximumPower", "Maximale Leistung:"))
    sensor_list.append(("OfflineOutputPower", "Offline-Ausgangsleistung:"))
    sensor_list.append(("NumberOfBatteries", "Batterien im System:"))
    sensor_list.append(("OutputOffset", "Ausgabe korrigieren:"))
    sensor_list.append(("CcuSpeed", "CCU-Geschwindigkeit:"))
    sensor_list.append(("Microinverter", "Mikro-Wechselrichter-Typ:"))
    sensor_list.append(("ResponseTolerance", "Reaktionstoleranz:"))
    sensor_list.append(("MinimumBatteryDischarge", "Minimale Entladung der Batterie:"))
    sensor_list.append(("MaximumBatteryCharge", "Maximale Akkuladung:"))
    sensor_list.append(("DC/DC-Algorithmus", "DC/DC-Algorithmus:"))
    sensor_list.append(("Cloudservice", "Cloudservice:"))
    sensor_list.append(("LocalServer", "Lokalen Server nutzen:"))
    sensor_list.append(("APIRoute", "API-Route:"))

    coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)    

    http_scan_sensor_list = []

    http_scan_sensor_list.append(
        HttpScanText(coordinator, "APIRoute", "API - Route", "mdi:link")
    )

    http_scan_sensor_list.append(
        HttpScanText(coordinator, "LocalServer", "Use Local Server", "mdi:server-off")
    )

    http_scan_sensor_list.append(
        HttpScanText(coordinator, "Cloudservice", "Cloudservice", "mdi:cloud-outline")
    )

    http_scan_sensor_list.append(
        HttpScanText(
            coordinator, "DC/DC-Algorithmus", "DC/DC algorithm", "mdi:source-branch"
        )
    )

    http_scan_sensor_list.append(
        HttpScanText(coordinator, "PowerMeterIp", "Power Meter IP", "mdi:ip")
    )

    http_scan_sensor_list.append(
        HttpScanText(coordinator, "PowerMeterType", "Power Meter Type", "mdi:chip")
    )
    http_scan_sensor_list.append(
        HttpScanText(coordinator, "MaximumPower", "Maximum Power", "mdi:flash")
    )
    http_scan_sensor_list.append(
        HttpScanText(
            coordinator, "OfflineOutputPower", "Offline Output Power", "mdi:flash"
        )
    )
    http_scan_sensor_list.append(
        HttpScanText(
            coordinator, "NumberOfBatteries", "Number of Batteries", "mdi:layers"
        )
    )
    http_scan_sensor_list.append(
        HttpScanText(coordinator, "OutputOffset", "Output Offset", "mdi:flash")
    )
    http_scan_sensor_list.append(
        HttpScanText(coordinator, "CcuSpeed", "CCU - Speed", "mdi:flash")
    )
    http_scan_sensor_list.append(
        HttpScanText(coordinator, "Microinverter", "Microinverter", "mdi:current-ac")
    )
    http_scan_sensor_list.append(
        HttpScanText(
            coordinator, "ResponseTolerance", "Response tolerance", "mdi:current-ac"
        )
    )

    http_scan_sensor_list.append(
        HttpScanText(
            coordinator,
            "MinimumBatteryDischarge",
            "Minimum Battery Discharge ",
            "mdi:battery-low",
        )
    )

    http_scan_sensor_list.append(
        HttpScanText(
            coordinator,
            "MaximumBatteryCharge",
            "Maximum Battery Charge ",
            "mdi:battery-high",
        )
    )    

    async_add_entities(
        [
            sensor,
            rssi_sensor,
            ccu_power,
            pv_power_sensor,
            battery_power_charge,
            battery_power_discharge,
            battery_soc,
            battery_power,
            power_meter,
            firmware_version,
            battery_soe,
            webhook_id,
            # power_consumption,
            grid_export,
            grid_import,
            # pv_self_consumption,
            *http_scan_sensor_list,
        ]
    )
    await asyncio.sleep(0)
    await coordinator.async_config_entry_first_refresh()

    pv_today_energy = PvTodayEnergy(hass, entry, pv_power_sensor.entity_id)
    pv_total_energy = PvTotalEnergy(hass, entry, pv_power_sensor.entity_id)
    ccu_energy_today = CcuEnergyToday(hass, entry, ccu_power.entity_id)
    ccu_energy_total = CcuEnergyTotal(hass, entry, ccu_power.entity_id)

    battery_today_energy_charge = BatteryTodayEnergyCharge(
        hass, entry, battery_power_charge.entity_id
    )
    battery_today_energy_discharge = BatteryTodayEnergyDischarge(
        hass, entry, battery_power_discharge.entity_id
    )

    battery_total_energy_charge = BatteryTotalEnergyCharge(
        hass, entry, battery_power_charge.entity_id
    )
    battery_total_energy_discharge = BatteryTotalEnergyDischarge(
        hass, entry, battery_power_discharge.entity_id
    )

    grid_export_energy_today = GridExportEnergyToday(hass, entry, grid_export.entity_id)
    grid_export_energy_total = GridExportEnergyTotal(hass, entry, grid_export.entity_id)

    grid_import_energy_today = GridImportEnergyToday(hass, entry, grid_import.entity_id)
    grid_import_energy_total = GridImportEnergyTotal(hass, entry, grid_import.entity_id)

    # pv_self_consumption_today = PvSelfConsumptionEnergyToday(
    #     hass, entry, pv_self_consumption.entity_id
    # )
    # pv_self_consumption_total = PvSelfConsumptionEnergyTotal(
    #     hass, entry, pv_self_consumption.entity_id
    # )

    async_add_entities(
        [
            pv_today_energy,
            pv_total_energy,
            ccu_energy_today,
            ccu_energy_total,
            battery_today_energy_charge,
            battery_today_energy_discharge,
            battery_total_energy_charge,
            battery_total_energy_discharge,
            grid_export_energy_today,
            grid_export_energy_total,
            grid_import_energy_today,
            grid_import_energy_total,
            # pv_self_consumption_today,
            # pv_self_consumption_total,
        ]
    )
