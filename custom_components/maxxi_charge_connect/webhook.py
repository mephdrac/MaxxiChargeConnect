"""Funktionen zum Registrieren und Abmelden von Webhooks.

Dieses Modul bietet Funktionen zum Registrieren und Abmelden von Webhooks
für den MaxxiChargeConnect-Integrationseintrag in Home Assistant.

Die Webhooks empfangen JSON-Daten, validieren optional die IP-Adresse des Anrufers
und senden empfangene Daten über den Dispatcher an registrierte Sensoren weiter.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from ipaddress import ip_address

from aiohttp import web
from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_DEVICE_ID,
    CONF_TIMEOUT_RECEIVE,
    DEFAULT_TIMEOUT_RECEIVE,
    DOMAIN,
    ERRORS,
    ONLY_ONE_IP,
    PROXY_ERROR_CCU,
    PROXY_ERROR_DEVICE_ID,
    WEBHOOK_LAST_UPDATE,
    WEBHOOK_NAME,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
    WEBHOOK_WATCHDOG_TASK,
)

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-locals, too-many-return-statements, too-many-statements
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

    entry_data = hass.data[DOMAIN][entry.entry_id]
    signal_sensor = f"{DOMAIN}_{entry.entry_id}_update_sensor"
    signal_stale = f"{DOMAIN}_{entry.entry_id}_sensor_stale"

    _LOGGER.info("Registering webhook '%s'", WEBHOOK_NAME)

    async def handle_webhook(hass: HomeAssistant, _webhook_id: str, request: web.Request):
        try:
            allowed_ip = entry.data.get(CONF_IP_ADDRESS, "")
            only_one_ip = entry.data.get(ONLY_ONE_IP, False)

            _LOGGER.debug("Hier: OnlyOneIp (%s)", only_one_ip)

            if only_one_ip:
                # IP des aufrufenden Geräts ermitteln
                peername = None
                if request.transport is not None:
                    peername = request.transport.get_extra_info("peername")

                if peername is None:
                    _LOGGER.warning("Konnte Peername nicht ermitteln – Zugriff verweigert")
                    return web.Response(status=403, text="Forbidden")

                remote_ip = peername[0]
                try:
                    ip_matches = ip_address(remote_ip) == ip_address(allowed_ip)
                except ValueError:
                    ip_matches = False
                if not ip_matches:
                    _LOGGER.warning("Zugriff verweigert für IP: %s", remote_ip)
                    return web.Response(status=403, text="Forbidden")

            data = await request.json()
            if entry_data.get(CONF_WEBHOOK_ID) != webhook_id:
                return web.Response(status=403, text="Forbidden")
            _LOGGER.debug("Webhook-Daten empfangen")

            # JSON-Validierung
            if not isinstance(data, dict):
                _LOGGER.error("Ungültige JSON-Datenstruktur: %s", type(data))
                return web.Response(status=400, text="Invalid JSON structure")

            # Erforderliche Felder prüfen
            required_fields = ["deviceId", "sendCount"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                _LOGGER.error("Fehlende erforderliche Felder: %s", missing_fields)
                return web.Response(status=400, text=f"Missing required fields: {missing_fields}")

            device_id = data[PROXY_ERROR_DEVICE_ID]
            if device_id == ERRORS:
                device_id = data.get(PROXY_ERROR_CCU)
            if not isinstance(device_id, str) or not device_id:
                return web.Response(status=400, text="Invalid deviceId")
            configured_id = entry.data.get(CONF_DEVICE_ID)
            issue_id = f"device_mismatch_{entry.entry_id}"
            if configured_id and device_id != configured_id:
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.CRITICAL,
                    translation_key="device_mismatch",
                    translation_placeholders={
                        "entry_title": entry.title,
                        "payload_device_id": device_id,
                        "config_device_id": configured_id,
                    },
                )
                return web.Response(status=403, text="Forbidden")

            ir.async_delete_issue(hass, DOMAIN, issue_id)

            # Doppelte Ausführung verhindern (basierend auf sendCount und Zeitstempel)
            send_count = data.get("sendCount")
            current_time = datetime.now(tz=UTC)
            _LOGGER.debug("Webhook sendCount: %s", send_count)
            _LOGGER.debug("Webhook current_time: %s", current_time)

            # Cache für letzte Verarbeitung
            cache_key = f"{entry.entry_id}_last_sendcount"
            last_sendcount = entry_data.get(cache_key)
            last_process_time = entry_data.get(f"{cache_key}_time")

            _LOGGER.debug("Webhook last_sendcount: %s", last_sendcount)
            _LOGGER.debug("Webhook last_process_time: %s", last_process_time)

            # Wenn gleicher sendCount innerhalb von 5 Sekunden → ignorieren
            if (
                last_sendcount == send_count
                and last_process_time
                and (current_time - last_process_time).total_seconds() < 5
            ):
                _LOGGER.warning("Doppelte Webhook-Ausführung erkannt (sendCount: %s), ignoriere", send_count)
                return web.Response(status=200, text="Duplicate request ignored")

            # Cache aktualisieren
            entry_data[cache_key] = send_count
            entry_data[f"{cache_key}_time"] = current_time

            record_v1_telemetry(hass, entry)
            async_dispatcher_send(hass, signal_sensor, data)

        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.error("Ungültige JSON-Daten empfangen")
            return web.Response(status=400, text="Invalid JSON")

        return web.Response(status=200, text="OK")

    async_register(
        hass,
        DOMAIN,
        WEBHOOK_NAME,
        webhook_id,
        handle_webhook,
    )
    entry_data[CONF_WEBHOOK_ID] = webhook_id
    entry_data[WEBHOOK_SIGNAL_UPDATE] = signal_sensor
    entry_data[WEBHOOK_SIGNAL_STATE] = signal_stale
    ir.async_delete_issue(hass, DOMAIN, f"device_mismatch_{webhook_id}")


async def async_unregister_webhook(hass: HomeAssistant, entry: ConfigEntry):
    """Meldet den Webhook für den angegebenen ConfigEntry ab."""

    task = hass.data[DOMAIN][entry.entry_id].get(WEBHOOK_WATCHDOG_TASK)
    if task:
        task.cancel()
        hass.data[DOMAIN][entry.entry_id][WEBHOOK_WATCHDOG_TASK] = None

    if webhook_id := hass.data[DOMAIN][entry.entry_id].pop(CONF_WEBHOOK_ID, None):
        _LOGGER.info("Unregistering webhook")
        async_unregister(hass, webhook_id)


def record_v1_telemetry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Refresh the reception timeout for webhook or local proxy telemetry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data[WEBHOOK_LAST_UPDATE] = datetime.now(tz=UTC)
    if entry_data.get(WEBHOOK_WATCHDOG_TASK) is None:
        entry_data[WEBHOOK_WATCHDOG_TASK] = hass.loop.create_task(_webhook_timeout_watcher(hass, entry))


async def _webhook_timeout_watcher(hass, entry):
    """Setzt Sensoren nach Timeout auf 'stale'."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    signal_stale = entry_data[WEBHOOK_SIGNAL_STATE]

    while True:
        await asyncio.sleep(4)
        last = entry_data.get(WEBHOOK_LAST_UPDATE)

        if last is None:
            continue

        timeout_receive = entry.data.get(CONF_TIMEOUT_RECEIVE, DEFAULT_TIMEOUT_RECEIVE)
        timeout_receive = max(timeout_receive, 5)

        delta = datetime.now(tz=UTC) - last

        if delta.total_seconds() > timeout_receive:
            # Zu lange her → alle Sensoren stale setzen
            entry_data.pop(WEBHOOK_LAST_UPDATE, None)
            async_dispatcher_send(hass, signal_stale, None)
            _LOGGER.warning(
                "Webhook-Timeout überschritten (%s Sekunden). Sensoren auf 'stale' gesetzt",
                timeout_receive,
            )
