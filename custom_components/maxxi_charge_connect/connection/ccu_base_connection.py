from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


class CcuBaseConnection:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry

    async def async_setup(self) -> None:
        raise NotImplementedError
    
    async def async_setup_entry(self) -> bool:
        raise NotImplementedError

    async def async_unload(self) -> None:
        raise NotImplementedError