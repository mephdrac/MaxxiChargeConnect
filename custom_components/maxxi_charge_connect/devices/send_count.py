"""Sensor zur Überwachung des SendCount-Zählers für MaxxiCharge-Geräte.

Dieser Sensor überwacht den sendCount-Wert, der die Anzahl der gesendeten Telegramme
vom Gerät repräsentiert. Er erkennt Lücken in der Kommunikation und Resets des Zählers,
um die Zuverlässigkeit der Datenübertragung zu überwachen.

Der Sensor ist als diagnostische Entität kategorisiert und liefert zusätzliche Attribute
wie fehlende Pakete, letzte Differenz und Anzahl der Resets.
"""

import logging
from homeassistant.components.sensor import (
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class SendCount(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der (`sendCount`)"""

    _attr_translation_key = "SendCount"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den SendCount-Sensor mit den Basisattributen.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz, die vom Benutzer gesetzt wurde.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 0
        self._attr_unique_id = f"{entry.entry_id}_send_count"
        self._attr_icon = "mdi:counter"
        self._attr_native_value = None
        self._attr_device_class = None
        # self._attr_native_unit_of_measurement = "telegrams"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        self._last_sendcount = None
        self._missing_packets = 0
        self._resets = 0
        self._last_delta = 0
        self._attr_available = True

    async def handle_update(self, data):
        """Behandelt eingehende Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Dictionary mit dem Schlüssel `sendCount`, der die momentane
                         Import-/Exportleistung repräsentiert.

        """
        new_value = data.get("sendCount")
        if new_value is None:
            _LOGGER.error("Wert für sendCount ist None")
            return

        # Typ-Konvertierung für String-Werte
        try:
            new_value = int(new_value)
        except (ValueError, TypeError):
            _LOGGER.error("Ungültiger sendCount Wert: %s", new_value)
            return

        self._process_sendcount(new_value)

    @property
    def extra_state_attributes(self):
        """Zusätzliche Attribute für Lücken und Reboots."""
        return {
            "missing_packets": self._missing_packets,
            "last_delta": self._last_delta,
            "resets": self._resets,
        }

    def _process_sendcount(self, new_value):
        """Prüft Lücken und Resets."""

        if self._last_sendcount is None:
            self._last_sendcount = new_value
            self._attr_native_value = new_value
            return

        self._attr_native_value = new_value

        delta = new_value - self._last_sendcount
        self._last_delta = delta

        if delta > 1:
            self._missing_packets += (delta - 1)
            _LOGGER.info("SendCount Lücke erkannt: %s fehlende Telegramme (Delta: %s)", delta - 1, delta)
        elif delta <= 0:
            self._resets += 1
            _LOGGER.info("SendCount Reset erkannt: %s -> %s (Delta: %s)", self._last_sendcount, new_value, delta)

        self._last_sendcount = new_value

    async def handle_stale(self):
        """Bei stale verfügbar bleiben und letzten Wert beibehalten."""
        self._attr_available = True
