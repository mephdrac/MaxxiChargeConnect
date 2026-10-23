"""Sensor setup for CCU V2."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN

from .battery_soc import BatterySoc
from .power_meter import PowerMeter
from .ccu_power import CcuPower
from .grid_import import GridImport
from .grid_export import GridExport
from .ccu_temperatur_sensor import CCUTemperaturSensor
from .device_id import DeviceId
from .online_status_sensor import OnlineStatusSensor
from .ccu_v2_battery_sensor_manager import CCUV2BatterySensorManager
from .battery_power_charge import BatteryPowerCharge
from .battery_power_discharge import BatteryPowerDischarge
from .battery_power import BatteryPower
from .power_consumption import PowerConsumption
from .ccu_energy_today import CcuEnergyToday
from .ccu_energy_total import CcuEnergyTotal

from .battery_today_energy_charge import BatteryTodayEnergyCharge
from .battery_today_energy_discharge import BatteryTodayEnergyDischarge
from .battery_total_energy_charge import BatteryTotalEnergyCharge
from .battery_total_energy_discharge import BatteryTotalEnergyDischarge
from .consumption_energy_today import ConsumptionEnergyToday
from .consumption_energy_total import ConsumptionEnergyTotal
from .grid_export_energy_today import GridExportEnergyToday
from .grid_export_energy_total import GridExportEnergyTotal
from .grid_import_energy_today import GridImportEnergyToday
from .grid_import_energy_total import GridImportEnergyTotal


def setup_v2_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors supported by CCU V2."""

    async_add_entities(
        [
            PowerMeter(entry),
            PowerConsumption(entry),
            BatterySoc(entry),
            BatteryPowerCharge(entry),
            BatteryPowerDischarge(entry),
            BatteryPower(entry),
            CcuPower(entry),
            GridImport(entry),
            GridExport(entry),
            CCUTemperaturSensor(entry),
            DeviceId(entry),
            OnlineStatusSensor(entry),
        ]
    )

    battery_manager = CCUV2BatterySensorManager(
        hass,
        entry,
        async_add_entities,
    )

    battery_manager.setup()

    setup_v2_battery_energy(
        hass,
        entry,
        async_add_entities,
    )

def setup_v2_battery_energy(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Register CCU V2 battery energy sensors."""

        energy_sensors = {
            "battery_power_charge": [
                BatteryTodayEnergyCharge,
                BatteryTotalEnergyCharge,
            ],
            "battery_power_discharge": [
                BatteryTodayEnergyDischarge,
                BatteryTotalEnergyDischarge
            ],
            "power_consumption": [
                ConsumptionEnergyToday,
                ConsumptionEnergyTotal
            ],
            "ccu_power": [
                CcuEnergyToday,
                CcuEnergyTotal
            ],
            "grid_export": [
                GridExportEnergyToday,
                GridExportEnergyTotal,
            ],
            "grid_import": [
                GridImportEnergyToday,
                GridImportEnergyTotal,
            ],
        }

        registered_sensors = set()

        @callback
        def try_add_energy_sensors() -> None:
            """Create energy sensors when their sources exist."""

            registry = er.async_get(hass)

            new_sensors = []

            for source_key, sensor_classes in energy_sensors.items():
                source_entity_id = registry.async_get_entity_id(
                    "sensor",
                    DOMAIN,
                    f"{entry.entry_id}_{source_key}",
                )

                if source_entity_id is None:
                    continue

                for sensor_class in sensor_classes:
                    sensor_key = sensor_class.__name__

                    if sensor_key in registered_sensors:
                        continue

                    new_sensors.append(
                        sensor_class(hass, entry, source_entity_id)
                    )

                    registered_sensors.add(sensor_key)

            if new_sensors:
                async_add_entities(new_sensors)

        @callback
        def handle_registry_update(event) -> None:
            """React to newly registered entities."""

            if event.data.get("action") == "create":
                try_add_energy_sensors()

        unsubscribe = hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            handle_registry_update,
        )

        entry.async_on_unload(unsubscribe)

        # Bereits vorhandene Quell-Entitäten berücksichtigen
        try_add_energy_sensors()