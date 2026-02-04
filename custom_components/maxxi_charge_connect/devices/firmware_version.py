"""TextEntity zur Anzeige der Firmware-Version eines Batteriesystems in Home Assistant.

Diese Entität zeigt die aktuelle Firmware-Version an, die über einen Webhook empfangen wird.
Sie ist als diagnostische Entität kategorisiert.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import Event

from ..const import (
    PROXY_STATUS_EVENTNAME,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
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

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Registriert sich beim Dispatcher, um auf eingehende Webhook-Daten zu reagieren.
        """
        await super().async_added_to_hass()

        if self._enable_cloud_data:
            _LOGGER.info("FirmwareVersion: Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self.handle_update(json_data)

    async def handle_update(self, data):
        """Verarbeitet empfangene Webhook-Daten und aktualisiert die Firmware-Version.

        Args:
            data (dict): Die empfangenen Daten vom Webhook.

        """
        try:
            firmware_raw = data.get("firmwareVersion")

            if firmware_raw is None:
                _LOGGER.debug("FirmwareVersion: firmwareVersion fehlt in den Daten")
                return

            # Konvertierung zu String und Bereinigung
            firmware = str(firmware_raw).strip()

            # Plausibilitätsprüfung: Firmware-Version sollte nicht leer sein
            if not firmware:
                _LOGGER.warning("FirmwareVersion: Leere firmwareVersion")
                return

            # Maximale Länge prüfen (typisch für Versions-Strings)
            if len(firmware) > 100:
                _LOGGER.warning(
                    "FirmwareVersion: Versionsstring zu lang: %s", firmware[:50] + "..."
                )
                return

            # Prüfen auf offensichtlich ungültige Werte
            invalid_patterns = ["unknown", "null", "undefined", "n/a"]
            if firmware.lower() in invalid_patterns:
                _LOGGER.debug("FirmwareVersion: Ungültiger Wert: %s", firmware)
                return

            self._attr_native_value = firmware
            _LOGGER.debug(
                "FirmwareVersion: Aktualisiert auf %s", self._attr_native_value
            )

        except (AttributeError, TypeError, ValueError) as err:
            _LOGGER.error("FirmwareVersion: Fehler bei der Verarbeitung: %s", err)

    def set_value(self, value):
        """SetValue für manuelle Wertsetzung."""
        if value and isinstance(value, str) and value.strip():
            cleaned_value = value.strip()
            if len(cleaned_value) <= 100:
                self._attr_native_value = cleaned_value
                _LOGGER.debug(
                    "FirmwareVersion: Manuell gesetzt auf %s", self._attr_native_value
                )
            else:
                _LOGGER.warning(
                    "FirmwareVersion: Ungültiger manueller Wert (zu lang): %s",
                    value[:50] + "...",
                )
        else:
            _LOGGER.warning("FirmwareVersion: Ungültiger manueller Wert: %s", value)

    def _restore_state_value(self, state_str: str):
        """Stellt den Zustand für Firmware-Version wieder her.

        Args:
            state_str: Der gespeicherte Zustand als String

        Returns:
            Der wiederhergestellte Wert im korrekten Typ oder None bei Fehler
        """
        # Für Text-Entity einfach den String zurückgeben
        try:
            firmware = str(state_str).strip()
            if firmware and len(firmware) <= 100:
                return firmware
        except (ValueError, TypeError):
            pass

        return None
