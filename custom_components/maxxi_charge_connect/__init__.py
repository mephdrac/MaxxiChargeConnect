import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .webhook import async_register_webhook, async_unregister_webhook

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    await async_register_webhook(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle migration of config entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        # Beispiel: wir fügen 'host' hinzu, wenn es ihn noch nicht gibt
        new_data = {**entry.data}

        if CONF_HOST not in new_data:
            new_data[CONF_HOST] = "maxxi.local"  # Oder ein sinnvoller Default

        # Nutze async_update_entry, um sowohl Daten als auch Versionsnummer zu aktualisieren
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Successfully migrated entry to version 2")
        return True

    # Wenn schon aktuell:
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await async_unregister_webhook(hass, entry)

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
