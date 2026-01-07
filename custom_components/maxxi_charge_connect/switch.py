import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .winterbetrieb.winterbetrieb import Winterbetrieb

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(  # pylint: disable=too-many-locals, too-many-statements
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:

    winterbetrieb = Winterbetrieb(entry)

    async_add_entities([winterbetrieb])
