from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
import logging

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN
from . import webhook

import time


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    start = time.perf_counter()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    hass.data[CONF_WEBHOOK_ID] = entry.data[CONF_WEBHOOK_ID]

    # Registriere Webhook nur einmal global beim Start
    if not hass.data.get(f"{DOMAIN}_webhook_registered"):
        await webhook.async_register_webhook(hass)
        hass.data[f"{DOMAIN}_webhook_registered"] = True

    # # ✅ beide Plattformen gleichzeitig laden
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    duration = time.perf_counter() - start
    _LOGGER.info("Setup of Maxxi took%.3f seconds", duration)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
