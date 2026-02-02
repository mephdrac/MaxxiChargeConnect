
import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class Uptime(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der (`Uptime`)"""

    _attr_translation_key = "Uptime"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den SendCount-Sensor mit den Basisattributen.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz, die vom Benutzer gesetzt wurde.

        """
        super().__init__(entry)        
        self._attr_unique_id = f"{entry.entry_id}_uptime"
        self._attr_icon = "mdi:clock-time-two-outline"
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_state_class = None

        self._last_sendcount = None
        self._missing_packets = 0
        self._resets = 0
        self._last_delta = 0
        self._attr_available = True

    async def handle_update(self, data):
        """Behandelt eingehende Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Dictionary mit dem Schlüssel `uptime`, der die momentane
                         Import-/Exportleistung repräsentiert.

        """
        new_value = data.get("uptime")
        if new_value is None:
            _LOGGER.error("Wert für uptime ist None")
            return

        self._attr_native_value = (datetime.now() - timedelta(milliseconds=new_value)).isoformat()
        self.async_write_ha_state()
    
