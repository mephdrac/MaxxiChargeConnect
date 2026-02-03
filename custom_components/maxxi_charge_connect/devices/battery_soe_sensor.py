"""Modul für die BatterySoESensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die den Ladezustand (State of Energy, SoE)
einer bestimmten Batterie darstellt, dynamische Aktualisierungen verarbeitet
und Geräteinformationen für Home Assistant bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatterySoESensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung des Ladezustands (SoE) einer bestimmten Batterie.

    Dieser Sensor zeigt die aktuelle Energie in Watt-Stunden einer bestimmten Batterie an.
    Die Daten werden von den Batterieinformationen im Webhook-Datenstrom extrahiert
    und auf Plausibilität geprüft.
    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatterySoESensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert einen BatterySoESensor.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_soe_{index}"
        self._attr_icon = "mdi:home-battery"
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

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
                    "BatterySoESensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs", 
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            soe_raw = battery_data.get("batteryCapacity")
            
            if soe_raw is None:
                _LOGGER.debug(
                    "BatterySoESensor[%s]: batteryCapacity fehlt", 
                    self._index
                )
                return

            # Konvertierung zu float
            soe = float(soe_raw)
            
            # Plausibilitätsprüfung: SoE sollte positiv sein (in Watt-Stunden)
            if soe < 0:
                _LOGGER.warning(
                    "BatterySoESensor[%s]: Unplausible SoE: %s Wh", 
                    self._index, soe
                )
                return

            # Obere Grenze für typische Batteriespeicher (max 100 kWh)
            if soe > 100000:
                _LOGGER.warning(
                    "BatterySoESensor[%s]: SoE zu hoch: %s Wh (erwartet <100000 Wh)", 
                    self._index, soe
                )
                return

            self._attr_native_value = soe
            _LOGGER.debug(
                "BatterySoESensor[%s]: Aktualisiert auf %s Wh", 
                self._index, soe
            )
            
        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatterySoESensor[%s]: Datenstrukturfehler: %s", 
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatterySoESensor[%s]: Konvertierungsfehler: %s", 
                self._index, err
            )
