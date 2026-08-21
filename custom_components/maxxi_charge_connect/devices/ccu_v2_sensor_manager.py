"""Sensor setup for CCU V2."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .battery_soc import BatterySoc
from .power_meter import PowerMeter


def setup_v2_sensors(
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors supported by CCU V2."""

    async_add_entities(
        [
            PowerMeter(entry),
            BatterySoc(entry),
        ]
    )