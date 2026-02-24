"""TextEntity zur Anzeige der Geräte-ID eines Batteriesystems in Home Assistant.

Diese Entität zeigt die eindeutige Geräte-ID (z.B. Seriennummer) an, die per Webhook
übermittelt wird. Sie dient primär Diagnosezwecken und ist in der Kategorie
'diagnostic' einsortiert.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class DeviceId(BaseWebhookSensor):
    """TextEntity für die Anzeige der Geräte-ID eines verbundenen Geräts.

    Dieser Sensor zeigt die eindeutige Geräte-ID des Systems an.
    Die Daten werden vom Webhook-Datenstrom extrahiert und auf Plausibilität geprüft.
    """

    _attr_translation_key = "device_id"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Entity zur Anzeige der Geräte-ID.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_deviceid"
        self._attr_icon = "mdi:identifier"
        self._attr_native_value = None

    async def handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert die Geräte-ID.

        Args:
            data (dict): Die per Webhook empfangenen Daten.

        """
        try:
            device_id = data.get("deviceId")

            if device_id is None:
                _LOGGER.error("DeviceId: deviceId fehlt in den Daten")
                return

            # Plausibilitätsprüfung: deviceId sollte ein nicht-leerer String sein
            if not isinstance(device_id, str) or not device_id.strip():
                _LOGGER.error("DeviceId: Ungültige deviceId: %s", device_id)
                return

            # Maximale Länge prüfen (typisch für Geräte-IDs)
            if len(device_id.strip()) > 100:
                _LOGGER.error(
                    "DeviceId: deviceId zu lang: %s", device_id[:50] + "..."
                )
                return

            self._attr_native_value = device_id.strip()
            _LOGGER.debug("DeviceId: Aktualisiert auf %s", self._attr_native_value)

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("DeviceId: Fehler bei der Verarbeitung: %s", err)
