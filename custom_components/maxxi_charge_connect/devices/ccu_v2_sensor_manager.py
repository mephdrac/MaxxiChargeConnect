"""Sensor setup for CCU V2."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er


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

from ..const import DOMAIN
from .battery_today_energy_charge import BatteryTodayEnergyCharge


def setup_v2_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors supported by CCU V2."""

    async_add_entities(
        [
            PowerMeter(entry),
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
        """Register battery charge energy when the source entity exists."""

        source_unique_id = f"{entry.entry_id}_battery_power_charge"

        energy_added = False

        @callback
        def try_add_energy_sensor() -> None:
            nonlocal energy_added

            if energy_added:
                return

            registry = er.async_get(hass)

            source_entity_id = registry.async_get_entity_id(
                "sensor",
                DOMAIN,
                source_unique_id,
            )

            if source_entity_id is None:
                return

            energy_sensor = BatteryTodayEnergyCharge(
                hass,
                entry,
                source_entity_id,
            )

            energy_added = True
            async_add_entities([energy_sensor])

        @callback
        def handle_registry_update(event) -> None:
            """Check whether the source entity has been registered."""

            if event.data.get("action") == "create":
                try_add_energy_sensor()

        # Auf neue Entity-Registry-Einträge reagieren
        unsubscribe = hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            handle_registry_update,
        )

        entry.async_on_unload(unsubscribe)

        # Falls die Quell-Entität bereits registriert ist
        try_add_energy_sensor()