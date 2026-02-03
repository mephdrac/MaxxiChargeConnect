"""Modul für die BatteryVoltageSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die die Spannung einer bestimmten Batterie darstellt,
dynamische Aktualisierungen verarbeitet und Geräteinformationen für Home Assistant bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatteryVoltageSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung der Spannung einer bestimmten Batterie.

    Dieser Sensor zeigt die aktuelle Spannung einer bestimmten Batterie in Volt an.
    Die Daten werden von den Batterieinformationen im Webhook-Datenstrom extrahiert,
    von mV zu V konvertiert und auf Plausibilität geprüft.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryVoltageSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryVoltageSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_voltage_sensor_{index}"
        self._attr_icon = "mdi:alpha-v-circle"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    async def handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.

        Args:
            data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.

        """
        try:
            # Batterieinformationen sicher abfragen
            batteries_info = data.get("batteriesInfo", [])
            if not batteries_info or self._index >= len(batteries_info):
                _LOGGER.debug(
                    "BatteryVoltageSensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            voltage_raw = battery_data.get("batteryVoltage")
            
            if voltage_raw is None:
                _LOGGER.debug(
                    "BatteryVoltageSensor[%s]: batteryVoltage fehlt", 
                    self._index
                )
                return

            # Konvertierung zu float und von mV zu V
            voltage_mv = float(voltage_raw)
            voltage = voltage_mv / 1000.0
            
            # Plausibilitätsprüfung: Spannung sollte im vernünftigen Bereich liegen (0-60V)
            if voltage < 0:
                _LOGGER.warning(
                    "BatteryVoltageSensor[%s]: Unplausible Spannung: %s V", 
                    self._index, voltage
                )
                return

            if voltage > 60:
                _LOGGER.warning(
                    "BatteryVoltageSensor[%s]: Spannung zu hoch: %s V (erwartet <60V)", 
                    self._index, voltage
                )
                return

            self._attr_native_value = voltage
            _LOGGER.debug(
                "BatteryVoltageSensor[%s]: Aktualisiert auf %s V", 
                self._index, voltage
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryVoltageSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryVoltageSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
