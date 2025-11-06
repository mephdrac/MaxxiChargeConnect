"""Sensor-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert den `GridExport`-Sensor, der die aktuelle Einspeiseleistung
ins öffentliche Stromnetz misst und anzeigt. Der Sensor bezieht seine Daten über
einen Dispatcher-Signalmechanismus aus einem Webhook, der durch die Integration ausgelöst wird.

Die gemessene Leistung (`Pr`) wird auf ihre Plausibilität überprüft und in positiver Form
angezeigt, wenn eine tatsächliche Einspeisung stattfindet (d. h. `Pr < 0`).

Classes:
    GridExport: Sensor-Entity zur Darstellung der Netz-Einspeiseleistung in Watt.

Dependencies:
    - homeassistant.components.sensor
    - homeassistant.config_entries
    - homeassistant.const
    - homeassistant.helpers.dispatcher
    - .tools.isPrOk
    - .const.DEVICE_INFO, .const.DOMAIN
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import is_pr_ok  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class GridExport(BaseWebhookSensor):
    """Sensor zur Anzeige der aktuellen Einspeiseleistung ins Netz.

    Dieser Sensor zeigt die aktuelle Leistung (in Watt) an, die ins Stromnetz
    eingespeist wird. Die Leistung wird als positiver Wert dargestellt,
    wenn Einspeisung erfolgt (Leistung < 0 im Eingangssignal).

    Attributes:
        _attr_translation_key (str): Schlüssel für die Übersetzung des Namens.
        _attr_has_entity_name (bool): Gibt an, dass die Entität einen eigenen Namen hat.

    Args:
        entry (ConfigEntry): Konfigurationseintrag der Integration.

    """

    _attr_translation_key = "GridExport"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den GridExport-Sensor.

        Args:
            entry (ConfigEntry): Konfigurationseintrag der Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_grid_export"
        self._attr_icon = "mdi:transmission-tower-import"
        self._attr_native_value = None

        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet eingehende Sensordaten vom Dispatcher.

        Args:
            data (dict): Datenpaket mit Messwerten, erwartet Schlüssel 'Pr'.

        Setzt den aktuellen Wert auf die positive Einspeiseleistung in Watt,
        falls der Wert plausibel ist.

        """

        pr = float(data.get("Pr", 0))
        if is_pr_ok(pr):
            self._attr_native_value = round(max(-pr, 0), 2)
            self.async_write_ha_state()
