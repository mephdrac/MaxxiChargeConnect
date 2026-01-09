"""Switch platform for MaxxiCharge Connect integration."""

# import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .winterbetrieb.winterbetrieb import Winterbetrieb

# _LOGGER = logging.getLogger(__name__)

# pylint: disable=unused-argument
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup switches for MaxxiCharge Connect integration."""

    winterbetrieb = Winterbetrieb(entry)
    async_add_entities([winterbetrieb])
