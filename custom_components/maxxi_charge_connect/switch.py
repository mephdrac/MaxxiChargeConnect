# import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .winterbetrieb.winterbetrieb import Winterbetrieb
from .const import DOMAIN, CONF_WINTER_MODE, DEFAULT_WINTER_MODE

#_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(  # pylint: disable=too-many-locals, too-many-statements
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup switches for MaxxiCharge Connect integration."""

    winter_mode = entry.options.get(
        CONF_WINTER_MODE,
        DEFAULT_WINTER_MODE,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONF_WINTER_MODE] = winter_mode

    winterbetrieb = Winterbetrieb(entry)
    async_add_entities([winterbetrieb])
