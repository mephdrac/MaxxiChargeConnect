import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .webhook import async_register_webhook, async_unregister_webhook
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    await async_register_webhook(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """No migration needed."""
    _LOGGER.debug("Migration called for entry: %s", config_entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await async_unregister_webhook(hass, entry)

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
