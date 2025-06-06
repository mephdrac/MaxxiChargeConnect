# PowerMeterIp.py
from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN


class NumberOfBatteries(TextEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Number of Batteries"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_number_of_batteries"
        self._attr_icon = "mdi:layers"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_should_poll = False

    @property
    def native_value(self):
        return (
            self.coordinator.data.get("NumberOfBatteries")
            if self.coordinator.data
            else None
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry.entry_id)},
            "name": self.coordinator.entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
