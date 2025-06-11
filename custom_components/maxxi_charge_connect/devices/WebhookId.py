from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory


class WebhookId(TextEntity):
    def __init__(self, entry: ConfigEntry):
        self._attr_native_value = entry.data[CONF_WEBHOOK_ID]
        #  self._unsub_dispatcher = None
        self._entry = entry
        self._attr_name = "Webhook ID"
        self._attr_unique_id = f"{entry.entry_id}_webhook_id"
        self._attr_icon = "mdi:webhook"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

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
