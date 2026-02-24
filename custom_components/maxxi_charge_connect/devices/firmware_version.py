"""TextEntity zur Anzeige der Firmware-Version eines Batteriesystems in Home Assistant.

Diese Entität zeigt die aktuelle Firmware-Version an, die über einen Webhook empfangen wird.
Sie ist als diagnostische Entität kategorisiert.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class FirmwareVersion(BaseWebhookSensor):
    """TextEntity zur Anzeige der Firmware-Version eines Geräts.

    Dieser Sensor zeigt die aktuelle Firmware-Version des Systems an.
    Die Daten werden vom Webhook-Datenstrom extrahiert und auf Plausibilität geprüft.
    """

    _attr_translation_key = "FirmwareVersion"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Entity für die Firmware-Version.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.

        """
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_firmware_version"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = None

    async def handle_update(self, data):
        """Verarbeitet empfangene Webhook-Daten und aktualisiert die Firmware-Version.

        Args:
            data (dict): Die empfangenen Daten vom Webhook.

        """
        try:
            firmware_raw = data.get("firmwareVersion")

            if firmware_raw is None:
                _LOGGER.error("FirmwareVersion: firmwareVersion fehlt in den Daten")
                return

            # Konvertierung zu String und Bereinigung
            firmware = str(firmware_raw).strip()

            # Plausibilitätsprüfung: Firmware-Version sollte nicht leer sein
            if not firmware:
                _LOGGER.error("FirmwareVersion: Leere firmwareVersion")
                return

            # Maximale Länge prüfen (typisch für Versions-Strings)
            if len(firmware) > 100:
                _LOGGER.error(
                    "FirmwareVersion: Versionsstring zu lang: %s", firmware[:50] + "..."
                )
                return

            # Prüfen auf offensichtlich ungültige Werte
            invalid_patterns = ["unknown", "null", "undefined", "n/a"]
            if firmware.lower() in invalid_patterns:
                _LOGGER.error("FirmwareVersion: Ungültiger Wert: %s", firmware)
                return

            self._attr_native_value = firmware
            _LOGGER.debug(
                "FirmwareVersion: Aktualisiert auf %s", self._attr_native_value
            )

        except (AttributeError, TypeError, ValueError) as err:
            _LOGGER.error("FirmwareVersion: Fehler bei der Verarbeitung: %s", err)
