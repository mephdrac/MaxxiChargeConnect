"""Modul für die BatteryPVPowerSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die die PV-Leistung einer bestimmten Batterie darstellt,
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

_LOGGER = logging.getLogger(__name__)


class BatteryPVPowerSensor(BaseWebhookSensor):
    """Sensor zur Überwachung und Anzeige der PV-Leistung einer Batterie.

    Dieser Sensor zeigt die aktuelle PV-Leistung (Photovoltaik-Leistung) einer bestimmten Batterie
    in Watt an. Die Daten werden von den Batterieinformationen im Webhook-Datenstrom
    extrahiert.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryPVPowerSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryPVPowerSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_pv_power_sensor_{index}"
        self._attr_icon = "mdi:alpha-v-circle"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        _LOGGER.debug("BatteryPVPowerSensor initialized for battery index %d", index)

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
                    "BatteryPVPowerSensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            pv_power_raw = battery_data.get("pvPower")
            
            if pv_power_raw is None:
                _LOGGER.debug(
                    "BatteryPVPowerSensor[%s]: pvPower fehlt", 
                    self._index
                )
                return

            # Konvertierung zu float
            pv_power = float(pv_power_raw)
            
            # Plausibilitätsprüfung: PV-Leistung sollte nicht negativ sein
            if pv_power < 0:
                _LOGGER.warning(
                    "BatteryPVPowerSensor[%s]: Negative PV-Leistung: %s W", 
                    self._index, pv_power
                )
                return

            # Plausibilitätsprüfung: Maximale PV-Leistung (z.B. 10kW)
            if pv_power > 10000:
                _LOGGER.warning(
                    "BatteryPVPowerSensor[%s]: Unplausible PV-Leistung: %s W", 
                    self._index, pv_power
                )
                return

            self._attr_native_value = pv_power
            _LOGGER.debug(
                "BatteryPVPowerSensor[%s]: Aktualisiert auf %s W", 
                self._index, pv_power
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryPVPowerSensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPVPowerSensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
