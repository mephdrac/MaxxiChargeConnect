"""Switch platform for MaxxiCharge Connect integration."""

# import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CCU_V2, CONF_CCU_VERSION
from .devices.mqtt_discovery_entity import setup_discovery_entities
from .winterbetrieb.winterbetrieb import Winterbetrieb

# _LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Setup switches for MaxxiCharge Connect integration."""

    if entry.data.get(CONF_CCU_VERSION) == CCU_V2:
        setup_discovery_entities(hass, entry, async_add_entities, "switch")
        return

    winterbetrieb = Winterbetrieb(entry)
    async_add_entities([winterbetrieb])
