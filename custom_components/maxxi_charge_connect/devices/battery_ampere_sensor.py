"""Modul für die BatteryAmpereSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die den Strom einer einzelnen Batterie darstellt,
dynamische Aktualisierungen verarbeitet und Geräteinformationen für Home Assistant bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent

from .base_webhook_sensor import BaseWebhookSensor
from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryAmpereSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung der Stromstärke einer bestimmten Batterie.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryAmpereSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryAmpereSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_ampere_sensor_{index}"
        self._attr_icon = "mdi:alpha-a-circle"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    async def handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.

        Args:
            data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.

        """
        try:
            batteries_info = data.get("batteriesInfo", [])
            
            if not batteries_info or self._index >= len(batteries_info):
                _LOGGER.debug(
                    "BatteryAmpereSensor[%s]: Keine Batterie-Daten oder Index außerhalb Bereich", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            battery_current = battery_data.get("batteryCurrent")
            
            if battery_current is None:
                _LOGGER.debug(
                    "BatteryAmpereSensor[%s]: batteryCurrent fehlt", 
                    self._index
                )
                return

            # Konvertiere mA zu A
            current_amps = float(battery_current) / 1000.0
            
            # Plausibilitätsprüfung: Strom sollte nicht extrem sein
            if abs(current_amps) > 200:  # 200A als vernünftige Obergrenze
                _LOGGER.warning(
                    "BatteryAmpereSensor[%s]: Unplausibler Stromwert: %s A", 
                    self._index, current_amps
                )
                return

            self._attr_native_value = current_amps
            _LOGGER.debug(
                "BatteryAmpereSensor[%s]: Aktualisiert auf %s A", 
                self._index, current_amps
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryAmpereSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryAmpereSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )