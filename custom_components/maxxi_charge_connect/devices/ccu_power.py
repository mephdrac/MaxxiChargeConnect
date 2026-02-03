"""Sensor-Entity zur Anzeige der aktuellen CCU-Leistung in Home Assistant.

Dieses Modul definiert die `CcuPower`-Klasse, die einen Sensor zur Messung der Leistung
(Pccu-Wert) einer CCU (Central Control Unit) bereitstellt. Die Daten werden per Webhook empfangen
und regelmäßig aktualisiert.

Die Klasse nutzt Home Assistants Dispatcher-System, um auf neue Sensordaten zu reagieren.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from .base_webhook_sensor import BaseWebhookSensor

from ..tools import is_pccu_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class CcuPower(BaseWebhookSensor):
    """SensorEntity für die aktuelle CCU-Leistung (Pccu-Wert).

    Diese Entität zeigt die aktuell gemessene Leistung in Watt an,
    wenn die empfangenen Daten als gültig eingestuft werden.
    """

    _attr_translation_key = "CcuPower"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den CCU-Leistungssensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "CCU Power"
        self._attr_unique_id = f"{entry.entry_id}_ccu_power"
        self._attr_icon = "mdi:power-plug-battery-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet neue Webhook-Daten und aktualisiert den Sensorzustand.

        Und prüft auf Plausibilität.

        Args:
            data (dict): Die per Webhook empfangenen Sensordaten.

        """
        pccu = float(data.get("Pccu", 0))

        if is_pccu_ok(pccu):
            self._attr_native_value = float(data.get("Pccu", 0))
            self.async_write_ha_state()
