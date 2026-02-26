"""Modul für die BatteryMpptVoltageSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die die MPPT-Spannung einer einzelnen Batterie darstellt,
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


class BatteryMpptVoltageSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung der MPPT-Spannung einer bestimmten Batterie.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryMpptVoltageSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryMpptVoltageSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_mppt_voltage_sensor_{index}"
        self._attr_icon = "mdi:alpha-v-circle"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    async def handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.

        Args:
            data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.

        """
        try:
            batteries_info = data.get("batteriesInfo", [])

            if not batteries_info or self._index >= len(batteries_info):
                _LOGGER.debug(
                    "BatteryMpptVoltageSensor[%s]: Keine Batterie-Daten oder Index außerhalb Bereich",
                    self._index,
                )
                return

            battery_data = batteries_info[self._index]
            mppt_voltage = battery_data.get("mpptVoltage")

            if mppt_voltage is None:
                _LOGGER.debug(
                    "BatteryMpptVoltageSensor[%s]: mpptVoltage fehlt", self._index
                )
                return

            # Konvertiere mV zu V
            mppt_volts = float(mppt_voltage) / 1000.0

            # Plausibilitätsprüfung: MPPT-Spannung sollte vernünftig sein
            if mppt_volts < 0 or mppt_volts > 100:  # 0-100V als vernünftiger Bereich
                _LOGGER.warning(
                    "BatteryMpptVoltageSensor[%s]: Unplausible MPPT-Spannung: %s V",
                    self._index,
                    mppt_volts,
                )
                return

            self._attr_native_value = mppt_volts
            _LOGGER.debug(
                "BatteryMpptVoltageSensor[%s]: Aktualisiert auf %s V",
                self._index,
                mppt_volts,
            )

        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryMpptVoltageSensor[%s]: Datenstrukturfehler: %s",
                self._index,
                err,
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryMpptVoltageSensor[%s]: Konvertierungsfehler: %s",
                self._index,
                err,
            )
