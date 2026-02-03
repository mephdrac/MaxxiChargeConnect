"""Modul für die BatteryChargeSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die die Ladeleistung einer einzelnen Batterie darstellt,
dynamische Aktualisierungen verarbeitet und Geräteinformationen für Home Assistant bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from .base_webhook_sensor import BaseWebhookSensor
from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryChargeSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung der Ladeleistung einer bestimmten Batterie.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatteryChargeSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryChargeSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_charge_sensor_{index}"
        self._attr_icon = "mdi:battery-plus-variant"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.

        Args:
            data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.

        """
        try:
            batteries_info = data.get("batteriesInfo", [])
            
            if not batteries_info or self._index >= len(batteries_info):
                _LOGGER.debug(
                    "BatteryChargeSensor[%s]: Keine Batterie-Daten oder Index außerhalb Bereich", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            battery_power = battery_data.get("batteryPower")
            
            if battery_power is None:
                _LOGGER.debug(
                    "BatteryChargeSensor[%s]: batteryPower fehlt", 
                    self._index
                )
                return

            # Konvertiere zu float
            charge_power = float(battery_power)
            
            # Nur positive Werte sind Ladeleistung
            if charge_power < 0:
                _LOGGER.debug(
                    "BatteryChargeSensor[%s]: Negative Leistung (%s W) - keine Ladeleistung", 
                    self._index, charge_power
                )
                return

            # Plausibilitätsprüfung: Ladeleistung sollte vernünftig sein
            if charge_power > 20000:  # 20kW als vernünftige Obergrenze
                _LOGGER.warning(
                    "BatteryChargeSensor[%s]: Unplausible Ladeleistung: %s W", 
                    self._index, charge_power
                )
                return

            self._attr_native_value = charge_power
            _LOGGER.debug(
                "BatteryChargeSensor[%s]: Aktualisiert auf %s W", 
                self._index, charge_power
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryChargeSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryChargeSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
