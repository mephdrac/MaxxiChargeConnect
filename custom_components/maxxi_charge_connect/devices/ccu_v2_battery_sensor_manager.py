"""Dynamic battery sensor management for CCU V2."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN, WEBHOOK_SIGNAL_UPDATE
from .battery_voltage_sensor import BatteryVoltageSensor

_LOGGER = logging.getLogger(__name__)


class CCUV2BatterySensorManager:
    """Dynamically create battery sensors for CCU V2."""

    SENSOR_CLASSES = [
        BatteryVoltageSensor,
    ]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the battery sensor manager."""
        self.hass = hass
        self.entry = entry
        self.async_add_entities = async_add_entities

        self._created_sensors = set()
        self._unsub_update = None

    def setup(self) -> None:
        """Subscribe to incoming CCU V2 updates."""

        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        update_signal = entry_data[WEBHOOK_SIGNAL_UPDATE]

        self._unsub_update = async_dispatcher_connect(
            self.hass,
            update_signal,
            self._handle_update,
        )

        self.entry.async_on_unload(self._unsub_update)

    def _handle_update(self, data: dict) -> None:
        """Schedule battery updates on the Home Assistant event loop."""

        self.hass.loop.call_soon_threadsafe(
            self._process_update,
            data,
        )


    def _process_update(self, data: dict) -> None:
        """Create missing battery sensors on the HA event loop."""

        batteries = data.get("batteriesInfo")

        if not isinstance(batteries, list) or not batteries:
            return

        new_sensors = []

        for index in range(len(batteries)):
            for sensor_class in self.SENSOR_CLASSES:

                sensor_key = (sensor_class, index)

                if sensor_key in self._created_sensors:
                    continue

                sensor = sensor_class(self.entry, index)

                new_sensors.append(sensor)
                self._created_sensors.add(sensor_key)

                _LOGGER.debug(
                    "Created %s for battery %s",
                    sensor_class.__name__,
                    index,
                )

        if new_sensors:
            self.async_add_entities(new_sensors)