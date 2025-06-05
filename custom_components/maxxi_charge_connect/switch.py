# from homeassistant.components.switch import SwitchEntity
# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.entity_platform import AddEntitiesCallback
# from .const import DOMAIN


# async def async_setup_entry(
#     hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
# ):
#     #async_add_entities([HelloWorldSwitch(entry)])


# class HelloWorldSwitch(SwitchEntity):
#     def __init__(self, entry: ConfigEntry):
#         self._attr_name = f"{entry.data.get('name', 'Hello')} Switch"
#         self._attr_unique_id = f"{entry.entry_id}_switch"
#         self._entry = entry
#         self._is_on = False

#     async def async_turn_on(self, **kwargs):
#         self._is_on = True
#         self.async_write_ha_state()

#     async def async_turn_off(self, **kwargs):
#         self._is_on = False
#         self.async_write_ha_state()

#     @property
#     def is_on(self):
#         return self._is_on

#     @property
#     def device_info(self):
#         return {
#             "identifiers": {(DOMAIN, self._entry.entry_id)},
#             "name": self._entry.title,
#             "manufacturer": "Maxxi GmbH",
#             "model": "Maxxicharge",
#         }
