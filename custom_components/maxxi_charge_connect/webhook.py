"""Funktionen zum Registrieren und Abmelden von Webhooks.

Dieses Modul bietet Funktionen zum Registrieren und Abmelden von Webhooks
für den MaxxiChargeConnect-Integrationseintrag in Home Assistant.

Die Webhooks empfangen JSON-Daten, validieren optional die IP-Adresse des Anrufers
und senden empfangene Daten über den Dispatcher an registrierte Sensoren weiter.
"""

import json
import logging

from aiohttp import web

from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, ONLY_ONE_IP, WEBHOOK_NAME

_LOGGER = logging.getLogger(__name__)


async def async_register_webhook(hass: HomeAssistant, entry: ConfigEntry):
    """Registriert einen Webhook für den angegebenen ConfigEntry.

    Der Webhook empfängt JSON-Daten und validiert optional die IP-Adresse
    des aufrufenden Geräts, falls in den Optionen konfiguriert.

    Die empfangenen Daten werden über den Dispatcher an verbundene Sensoren weitergeleitet.

    Args:
        hass (HomeAssistant): Die Home Assistant Instanz.
        entry (ConfigEntry): Die Konfigurationseintrag, für den der Webhook registriert wird.

    Returns:
        None

    """
    webhook_id = entry.data[CONF_WEBHOOK_ID]

    # Vorherigen Handler entfernen, falls vorhanden
    try:
        async_unregister(hass, webhook_id)
        _LOGGER.warning("Alter Webhook mit ID %s wurde entfernt.", webhook_id)
    except Exception:  # pylint: disable=broad-exception-caught
        _LOGGER.debug("Kein bestehender Webhook für ID %s gefunden.", webhook_id)

    signal_sensor = f"{DOMAIN}_{webhook_id}_update_sensor"

    _LOGGER.info("Registering webhook '%s'", WEBHOOK_NAME)

    # async def handle_webhook(webhook_id, request):

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ):
        try:
            allowed_ip = entry.data.get(CONF_IP_ADDRESS, "")
            only_one_ip = entry.data.get(ONLY_ONE_IP, False)

            _LOGGER.debug("Hier: OnlyOneIp (%s)", only_one_ip)

            if only_one_ip:
                # IP des aufrufenden Geräts ermitteln
                peername = request.transport.get_extra_info("peername")

                if peername is None:
                    _LOGGER.warning(
                        "Konnte Peername nicht ermitteln – Zugriff verweigert"
                    )
                    return web.Response(status=403, text="Forbidden")

                remote_ip, _ = peername

                if remote_ip != allowed_ip:
                    _LOGGER.warning("Zugriff verweigert für IP: %s", remote_ip)
                    return web.Response(status=403, text="Forbidden")

            data = await request.json()
            _LOGGER.debug("Webhook [%s] received data: %s", webhook_id, data)
            async_dispatcher_send(hass, signal_sensor, data)
        except json.JSONDecodeError as e:
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        return web.Response(status=200, text="OK")

    async_register(
        hass,
        DOMAIN,
        WEBHOOK_NAME,
        webhook_id,
        handle_webhook,
    )


async def async_unregister_webhook(
    hass: HomeAssistant, entry: ConfigEntry, old_webhook_id: str | None = None
):
    """Meldet den Webhook für den angegebenen ConfigEntry ab."""
    webhook_id = old_webhook_id or entry.data[CONF_WEBHOOK_ID]
    _LOGGER.info("Unregistering webhook with ID: %s", webhook_id)

    async_unregister(hass, webhook_id)
