"""Sensor-Entity zur Anzeige der Uptime in Home Assistant.

Uptime wird in Milliesekunden angegeben.
Die Klasse nutzt Home Assistants Dispatcher-System, um auf neue Sensordaten zu reagieren.
"""

from datetime import UTC, datetime, timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class UptimeSensor(BaseWebhookSensor):
    """SensorEntity für die aktuelle Uptime (uptime).

    Diese Entität zeigt umgerechnet in Tage, Stunden, Minuten und Sekunden an.
    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "UptimeSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den UptimeSensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_uptime_sensor"
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._last_state_update = None

    async def handle_update(self, data):
        """Verarbeitet neue Webhook-Daten und aktualisiert den Sensorzustand.

        Und prüft auf Plausibilität.

        Args:
            data (dict): Die per Webhook empfangenen Sensordaten.

        """
        try:
            uptime_ms = int(data.get("uptime", 0))
            now_utc = datetime.now(tz=UTC)

            # State nur einmal am Tag aktualisieren
            if (self._last_state_update is None) or (
                now_utc - self._last_state_update >= timedelta(days=1)
            ):
                start_time_utc = now_utc - timedelta(milliseconds=uptime_ms)
                self._attr_native_value = start_time_utc
                self._last_state_update = now_utc

            # lesbares Format als extra attribute
            seconds_total = uptime_ms / 1000
            days, remainder = divmod(int(seconds_total), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            self._attr_extra_state_attributes = {
                "uptime": f"{days}d {hours}h {minutes}m {seconds}s",
                "raw_ms": uptime_ms,
            }
            self.async_write_ha_state()

        except ValueError as e:
            _LOGGER.warning("Uptime-Wert ungültig: %s", e)
