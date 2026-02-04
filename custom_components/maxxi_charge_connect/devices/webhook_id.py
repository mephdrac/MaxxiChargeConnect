"""Modul definiert die TextEntity `WebhookId`.

Dieses Modul definiert die TextEntity `WebhookId`, die die Webhook-ID
einer Integration als Textsensor in Home Assistant bereitstellt.
"""

import logging
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class WebhookId(TextEntity):
    """TextEntity zur Darstellung der Webhook-ID aus der ConfigEntry.

    Attributes:
        _entry (ConfigEntry): Die Konfigurationseintrag der Integration.
        _attr_native_value (str): Die aktuelle Webhook-ID als Text.
        _attr_name (str): Anzeigename der Entity.
        _attr_unique_id (str): Eindeutige ID der Entity.
        _attr_icon (str): Icon der Entity.
        _attr_entity_category (EntityCategory): Kategorie der Entity, hier DIAGNOSTIC.

    """

    _attr_translation_key = "WebhookId"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die WebhookId-TextEntity.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag der Integration.

        """
        self._entry = entry

        # Sichere Abfrage der Webhook-ID
        webhook_id = entry.data.get(CONF_WEBHOOK_ID)
        if webhook_id is None:
            _LOGGER.error("WebhookId: CONF_WEBHOOK_ID nicht in ConfigEntry gefunden")
            webhook_id = "unbekannt"
        elif not webhook_id:
            _LOGGER.warning("WebhookId: CONF_WEBHOOK_ID ist leer")
            webhook_id = "leer"
        else:
            _LOGGER.info("WebhookId: Initialisiert mit ID: %s", webhook_id)

        self._attr_native_value = webhook_id
        self._attr_unique_id = f"{entry.entry_id}_webhook_id"
        self._attr_icon = "mdi:webhook"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def set_value(self, value):
        """Setzt einen neuen Webhook-ID Wert."""
        _LOGGER.info(
            "WebhookId: Wert geändert von %s zu %s", self._attr_native_value, value
        )
        self._attr_native_value = value

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
