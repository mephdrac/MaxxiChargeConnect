"""Sensor setup for CCU V2."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .battery_soc import BatterySoc
from .power_meter import PowerMeter
from .ccu_power import CcuPower
from .grid_import import GridImport
from .grid_export import GridExport
from .ccu_temperatur_sensor import CCUTemperaturSensor
from .device_id import DeviceId
from .online_status_sensor import OnlineStatusSensor
from .ccu_v2_battery_sensor_manager import CCUV2BatterySensorManager


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