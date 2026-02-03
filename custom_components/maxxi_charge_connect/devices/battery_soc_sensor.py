"""Modul für die BatterySOCSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die den SOC einer bestimmten Batterie darstellt,
dynamische Aktualisierungen verarbeitet und Geräteinformationen für Home Assistant bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatterySOCSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung des SOC einer bestimmten Batterie."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatterySOCSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatterySOCSensor-Entität."""
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_soc_sensor_{index}"
        self._attr_icon = "mdi:home-battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    async def handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert."""
        try:
            # Batterieinformationen sicher abfragen
            batteries_info = data.get("batteriesInfo", [])
            if not batteries_info or self._index >= len(batteries_info):
                _LOGGER.debug(
                    "BatterySOCSensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            soc_raw = battery_data.get("batterySOC")
            
            if soc_raw is None:
                _LOGGER.debug(
                    "BatterySOCSensor[%s]: batterySOC fehlt", 
                    self._index
                )
                return

            # Konvertierung zu float
            soc = float(soc_raw)
            
            # Plausibilitätsprüfung: SOC sollte zwischen 0 und 100% liegen
            if soc < 0 or soc > 100:
                _LOGGER.warning(
                    "BatterySOCSensor[%s]: Unplausible SOC: %s%%", 
                    self._index, soc
                )
                return

            self._attr_native_value = soc
            _LOGGER.debug(
                "BatterySOCSensor[%s]: Aktualisiert auf %s%%", 
                self._index, soc
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatterySOCSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatterySOCSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
