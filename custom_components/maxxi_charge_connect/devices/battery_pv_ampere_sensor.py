"""Modul für die BatteryPVAmpereSensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, die den PV-Strom einer bestimmten Batterie darstellt,
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

_LOGGER = logging.getLogger(__name__)


class BatteryPVAmpereSensor(BaseWebhookSensor):
    """Sensor-Entität zur Darstellung des PV-Stroms einer bestimmten Batterie.

    Dieser Sensor zeigt den aktuellen PV-Strom (Photovoltaik-Strom) einer bestimmten Batterie
    in Ampere an. Die Daten werden von den Batterieinformationen im Webhook-Datenstrom
    extrahiert und von mA in A umgerechnet.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryPVAmpereSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryPVAmpereSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_pv_ampere_sensor_{index}"
        self._attr_icon = "mdi:alpha-a-circle"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

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
                    "BatteryPVAmpereSensor[%s]: batteriesInfo leer oder Index außerhalb des Bereichs",
                    self._index
                )
                return

            battery_data = batteries_info[self._index]
            pv_current_raw = battery_data.get("pvCurrent")

            if pv_current_raw is None:
                _LOGGER.debug(
                    "BatteryPVAmpereSensor[%s]: pvCurrent fehlt",
                    self._index
                )
                return

            # Konvertierung von mA zu A
            pv_current = float(pv_current_raw) / 1000.0

            # Plausibilitätsprüfung: PV-Strom sollte nicht negativ sein
            if pv_current < 0:
                _LOGGER.warning(
                    "BatteryPVAmpereSensor[%s]: Negativer PV-Strom: %s A",
                    self._index, pv_current
                )
                return

            # Plausibilitätsprüfung: Maximaler PV-Strom (z.B. 100A)
            if pv_current > 100:
                _LOGGER.warning(
                    "BatteryPVAmpereSensor[%s]: Unplausibler PV-Strom: %s A",
                    self._index, pv_current
                )
                return

            self._attr_native_value = pv_current
            _LOGGER.debug(
                "BatteryPVAmpereSensor[%s]: Aktualisiert auf %s A",
                self._index, pv_current
            )

        except (IndexError, KeyError) as err:
            _LOGGER.warning(
                "BatteryPVAmpereSensor[%s]: Datenstrukturfehler: %s",
                self._index, err
            )
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPVAmpereSensor[%s]: Konvertierungsfehler: %s",
                self._index, err
            )
