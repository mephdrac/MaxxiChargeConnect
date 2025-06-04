import logging

from aiohttp import web

from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, WEBHOOK_NAME
from homeassistant.const import CONF_WEBHOOK_ID


# SIGNAL_UPDATE_SENSOR = f"{DOMAIN}_{WEBHOOK_ID}_update_sensor"

_LOGGER = logging.getLogger(__name__)


async def async_register_webhook(hass: HomeAssistant):
    """Registriere Webhook im Home Assistant Core."""

    signal_sensor = f"{DOMAIN}_{hass.data[CONF_WEBHOOK_ID]}_update_sensor"

    _LOGGER.info(
        "Register webhook '%s' with ID: %s", WEBHOOK_NAME, hass.data[CONF_WEBHOOK_ID]
    )

    async def handle_webhook(hass, webhook_id, request):
        try:
            data = await request.json()
            # _LOGGER.warning("Empfangene Webhook-Daten: %s", data)
            async_dispatcher_send(hass, signal_sensor, data)
        except Exception as e:
            _LOGGER.error("Error on receiving webhook-data: %s", e)
            return web.Response(status=400, text="Invalid request")
        return web.Response(status=200, text="OK")

    async_register(
        hass,
        DOMAIN,
        WEBHOOK_NAME,
        hass.data[CONF_WEBHOOK_ID],
        handle_webhook,
    )

    _LOGGER.info("Webhook '%s' registered successful", WEBHOOK_NAME)


async def async_unregister_webhook(hass: HomeAssistant):
    """Webhook wieder entfernen."""
    async_unregister(hass, hass.data[CONF_WEBHOOK_ID])
