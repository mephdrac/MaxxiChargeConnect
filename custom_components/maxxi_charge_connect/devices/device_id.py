"""TextEntity zur Anzeige der Geräte-ID eines Batteriesystems in Home Assistant.

Diese Entität zeigt die eindeutige Geräte-ID (z. B. Seriennummer) an, die per Webhook
übermittelt wird. Sie dient primär Diagnosezwecken und ist in der Kategorie
'diagnostic' einsortiert.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import Event

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
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

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Verbindet sich mit dem Dispatcher-Signal, um auf eingehende Webhook-Daten zu reagieren.
        """
        await super().async_added_to_hass()

        if self._enable_cloud_data:
            _LOGGER.info("DeviceId: Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self.handle_update(json_data)

    async def handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert die Geräte-ID.

        Args:
            data (dict): Die per Webhook empfangenen Daten.

        """
        try:
            device_id = data.get("deviceId")
            
            if device_id is None:
                _LOGGER.debug("DeviceId: deviceId fehlt in den Daten")
                return
            
            # Plausibilitätsprüfung: deviceId sollte ein nicht-leerer String sein
            if not isinstance(device_id, str) or not device_id.strip():
                _LOGGER.warning("DeviceId: Ungültige deviceId: %s", device_id)
                return
            
            # Maximale Länge prüfen (typisch für Geräte-IDs)
            if len(device_id.strip()) > 100:
                _LOGGER.warning("DeviceId: deviceId zu lang: %s", device_id[:50] + "...")
                return

            self._attr_native_value = device_id.strip()
            _LOGGER.debug("DeviceId: Aktualisiert auf %s", self._attr_native_value)
            
        except Exception as err:
            _LOGGER.error("DeviceId: Fehler bei der Verarbeitung: %s", err)

    def set_value(self, value):
        """SetValue für manuelle Wertsetzung."""
        if value and isinstance(value, str) and value.strip():
            self._attr_native_value = value.strip()
            _LOGGER.debug("DeviceId: Manuell gesetzt auf %s", self._attr_native_value)
        else:
            _LOGGER.warning("DeviceId: Ungültiger manueller Wert: %s", value)

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
