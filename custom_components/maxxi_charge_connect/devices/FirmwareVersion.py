from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect


class FirmwareVersion(TextEntity):
    def __init__(self, entry: ConfigEntry):
        self._unsub_dispatcher = None
        self._entry = entry
        self._attr_name = "Firmware Version"
        self._attr_unique_id = f"{entry.entry_id}_firmware_version"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        value = str(data.get("firmwareVersion", "unknown"))
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
