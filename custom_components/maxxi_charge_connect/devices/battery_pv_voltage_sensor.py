"""Modul für die BatteryPVVoltageSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die die PV-Spannung einer bestimmten Batterie darstellt,
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


class BatteryPVVoltageSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung der PV-Spannung einer bestimmten Batterie.

    Dieser Sensor zeigt die aktuelle PV-Spannung (Photovoltaik-Spannung) einer bestimmten Batterie
    in Volt an. Die Daten werden von den Batterieinformationen im Webhook-Datenstrom
    extrahiert und von mV in V umgerechnet.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryPVVoltageSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryPVVoltageSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_pv_voltage_sensor_{index}"
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
                    "BatteryPVVoltageSensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            pv_voltage_raw = battery_data.get("pvVoltage")
            
            if pv_voltage_raw is None:
                _LOGGER.debug(
                    "BatteryPVVoltageSensor[%s]: pvVoltage fehlt", 
                    self._index
                )
                return

            # Konvertierung von mV zu V
            pv_voltage = float(pv_voltage_raw) / 1000.0
            
            # Plausibilitätsprüfung: PV-Spannung sollte nicht negativ sein
            if pv_voltage < 0:
                _LOGGER.warning(
                    "BatteryPVVoltageSensor[%s]: Negative PV-Spannung: %s V", 
                    self._index, pv_voltage
                )
                return

            # Plausibilitätsprüfung: Maximale PV-Spannung (z.B. 100V)
            if pv_voltage > 100:
                _LOGGER.warning(
                    "BatteryPVVoltageSensor[%s]: Unplausible PV-Spannung: %s V", 
                    self._index, pv_voltage
                )
                return

            self._attr_native_value = pv_voltage
            _LOGGER.debug(
                "BatteryPVVoltageSensor[%s]: Aktualisiert auf %s V", 
                self._index, pv_voltage
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryPVVoltageSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPVVoltageSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
