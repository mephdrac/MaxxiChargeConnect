"""Proxy-Server zum Abfangen der Meldungen an die MaxxiCloud"""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_ERROR_CODE,
    PROXY_ERROR_EVENTNAME,
    PROXY_ERROR_MESSAGE,
    PROXY_ERROR_TOTAL,
    PROXY_ERROR_CCU,
    PROXY_ERROR_IP,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)


class ErrorSensor(SensorEntity):
    """Entity für die Anzeige des Fehlerstatus eines verbundenen Geräts."""

    _attr_translation_key = "ErrorSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Entity zur Anzeige des Fehlerstatus.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_error_sensor"
        self._attr_icon = "mdi:alert-circle"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._device_id = self._entry.data.get(CONF_DEVICE_ID)

        # Hier die Zusatzinfos
        self._error_code = None
        self._error_message = None
        self._total_errors = None
        self._ip_addr = None

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen."""

        # Event-Listener registrieren
        self.async_on_remove(
            self.hass.bus.async_listen(PROXY_ERROR_EVENTNAME, self._handle_error_event)
        )

    async def _handle_error_event(self, event):
        data = event.data

        if data.get(PROXY_ERROR_DEVICE_ID) != self._device_id:
            return  # Falls mehrere Geräte existieren

        self._error_message = data.get(PROXY_ERROR_MESSAGE)

        # State = "Fehler" oder "OK"
        self._attr_native_value = (
            self._error_message if data.get(PROXY_ERROR_CODE) else "OK"
        )

        if self._attr_native_value == "OK":
            await self.hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": f"maxxicharge_error_{self._entry.entry_id}"},
            )
        else:
            # Zusatzattribute speichern
            self._error_code = data.get(PROXY_ERROR_CODE)
            self._error_message = data.get(PROXY_ERROR_MESSAGE)
            self._total_errors = data.get(PROXY_ERROR_TOTAL)
            self._ip_addr = data.get(PROXY_ERROR_IP)

            # Notification senden
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "MaxxiCharge Fehler",
                    "message": f"{self._error_message} (Code {self._error_code})",
                    "notification_id": f"maxxicharge_error_{self._entry.entry_id}",
                },
            )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Zusatzinfos, die im Pop-up erscheinen."""
        return {
            "Fehlercode": self._error_code,
            "Fehlermeldung": self._error_message,
            "Gesamtanzahl Fehler": self._total_errors,
            "IP-Adresse": self._ip_addr,
        }

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """

        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
