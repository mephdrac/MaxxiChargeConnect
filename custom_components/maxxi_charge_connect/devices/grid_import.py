"""Sensor zur Messung der aktuellen Netzimportleistung für Home Assistant.

Dieses Modul definiert die Entität `GridImport`, die die vom Stromnetz
importierte Leistung (in Watt) darstellt. Die Werte werden per Webhook übermittelt
und bei neuen Daten aktualisiert.
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


class GridImport(BaseWebhookSensor):
    """Sensor-Entität für importierte Leistung aus dem Stromnetz (Grid Import).

    Diese Entität empfängt Leistungsdaten über einen internen Dispatcher
    (z.B. ausgelöst durch einen Webhook) und aktualisiert den aktuellen
    Leistungswert (Watt).
    """

    _attr_translation_key = "GridImport"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die GridImport-Sensor-Entität.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für die Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_grid_import"
        self._attr_icon = "mdi:transmission-tower-export"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet eingehende Leistungsdaten.

        Args:
            data (dict): Ein Dictionary mit Sensordaten, typischerweise aus einem Webhook.
                         Erwartet den Schlüssel `"Pr"` für Netzimport-Leistung (W).

        """
        pr = float(data.get("Pr", 0))
        if is_pr_ok(pr):
            self._attr_native_value = max(pr, 0)
            self.async_write_ha_state()
