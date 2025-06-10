import logging

from aiohttp import web

from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, WEBHOOK_NAME

_LOGGER = logging.getLogger(__name__)


async def async_register_webhook(hass: HomeAssistant, entry: ConfigEntry):
    """Webhook registrieren, spezifisch für diesen ConfigEntry."""

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    signal_sensor = f"{DOMAIN}_{webhook_id}_update_sensor"

    _LOGGER.info("Registering webhook '%s'", WEBHOOK_NAME)

    async def handle_webhook(hass, webhook_id, request):
        try:
            allowed_ip = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
            # _LOGGER.warning("Allowed_ip (%s)", allowed_ip)

            # IP des aufrufenden Geräts ermitteln
            peername = request.transport.get_extra_info("peername")

            if peername is None:
                _LOGGER.warning("Konnte Peername nicht ermitteln – Zugriff verweigert")
                return web.Response(status=403, text="Forbidden")

            remote_ip, _ = peername
            _LOGGER.debug("Webhook-Aufruf von IP: %s", remote_ip)

            if remote_ip != allowed_ip:
                _LOGGER.warning("Zugriff verweigert für IP: %s", remote_ip)
                return web.Response(status=403, text="Forbidden")

            _LOGGER.info("Zugriff erlaubt für IP: %s", remote_ip)

            data = await request.json()
            _LOGGER.debug("Webhook [%s] received data: %s", webhook_id, data)
            async_dispatcher_send(hass, signal_sensor, data)
        except Exception as e:
            _LOGGER.error("Error processing webhook data: %s", e)
            return web.Response(status=400, text="Invalid request")
        return web.Response(status=200, text="OK")

    async_register(
        hass,
        DOMAIN,
        WEBHOOK_NAME,
        webhook_id,
        handle_webhook,
    )


async def async_unregister_webhook(hass: HomeAssistant, entry: ConfigEntry):
    webhook_id = entry.data[CONF_WEBHOOK_ID]
    _LOGGER.info("Unregistering webhook with ID: %s", webhook_id)
    async_unregister(hass, webhook_id)
