from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory


from ..const import DOMAIN


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
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
