import logging

# from homeassistant.core import HomeAssistant
# from homeassistant.config_entries import ConfigEntry

from .ccu_base_connection import CcuBaseConnection

_LOGGER = logging.getLogger(__name__)


class ccuV2Connection(CcuBaseConnection):
    
    # def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
    #     super().__init__(hass, entry)
    
    async def async_setup(self) -> None:
        raise NotImplementedError

    async def async_setup_entry(self) -> bool:
        raise NotImplementedError

    async def async_unload(self) -> None:
        raise NotImplementedError
