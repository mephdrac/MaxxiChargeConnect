"""Das Modul enthält die Reverse-Proxy.

Der Reverse-Proxy dient dazu, die Daten die an maxxisun.app geschickt werden,
abzufangen und an die Integration weiter zu geben. Des weiteren können
die Daten an die reale Cloud weiter geschickt werden. Es werden keine Daten
manipuliert."""

import logging
import asyncio
from typing import List, Optional

import dns.resolver

from aiohttp import web, ClientSession, ClientError

from ..const import (
    PROXY_ERROR_EVENTNAME,
    PROXY_ERROR_DEVICE_ID,
    PROXY_ERROR_CODE,
    PROXY_ERROR_MESSAGE,
    PROXY_ERROR_TOTAL,
    PROXY_ERROR_CCU,
    PROXY_ERROR_IP,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiProxyServer:
    """Definition des Reverse-Proxy"""

    def __init__(self, hass, listen_port=3001, enable_forward=False):
        """Constructor"""

        self.hass = hass
        self.listen_port = listen_port
        self.enable_forward_to_cloud = enable_forward
        self.runner = None

    async def _handle_text(self, request):
        """Liefert den Statustext, der vom Maxxigerät an die Cloud gesendet wird"""
        try:
            data = await request.json()

        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        _LOGGER.debug("Lokaler Maxxi-Fehler empfangen: %s", data)

        # Beispiel: Aktuellen Fehler als HA-State speichern
        self.hass.states.async_set("maxxichargeconnect.last_error", str(data))
        await self._on_reverse_proxy_message(data)

        # An echte Cloud weiterleiten
        if self.enable_forward_to_cloud:
            _LOGGER.debug("Forwarding to cloud is enabled")

            try:
                ip = await self.resolve_external("maxxisun1.app")
                _LOGGER.debug("maxxisun.app - ip = %s", ip)

                async with ClientSession() as session:
                    async with session.post(ip, json=data) as resp:
                        cloud_resp = await resp.text()
                        _LOGGER.debug(
                            "Antwort der echten Cloud (%s): %s", ip, cloud_resp
                        )

            except ClientError as e:
                _LOGGER.error("Cloud-Weiterleitung fehlgeschlagen: %s", e)
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error("Unerwarteter Fehler bei Cloud-Weiterleitung: %s", e)
        return web.Response(status=200, text="OK")

    async def start(self):
        """Startet den Reverse-Proxy und hört auf Port 3001"""
        app = web.Application()
        app["hass"] = self.hass
        app.router.add_post("/text", self._handle_text)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.listen_port)
        await site.start()

        _LOGGER.info("Maxxi-Proxy-Server gestartet auf Port %s", self.listen_port)

    async def stop(self):
        """Beendet den Reverse-Proxy"""
        if self.runner:
            await self.runner.cleanup()
            _LOGGER.info("Maxxi-Proxy-Server gestoppt")

    async def resolve_external(
        self, domain: str, nameservers: Optional[List[str]] = None

    ) -> str:
        """Löst den realen maxxisun.app auf - für das Cloud-Forwarding"""
        if nameservers is None:
            nameservers = ["8.8.8.8", "1.1.1.1"]

        loop = asyncio.get_running_loop()

        def blocking_resolve():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers  # z.B. Cloudflare DNS
            answers = resolver.resolve(domain, "A")
            return answers[0].to_text()

        ip = await loop.run_in_executor(None, blocking_resolve)
        return ip

    async def _on_reverse_proxy_message(self, json_data):
        self.hass.bus.async_fire(
            PROXY_ERROR_EVENTNAME,
            {
                PROXY_ERROR_DEVICE_ID: json_data.get(PROXY_ERROR_DEVICE_ID),
                PROXY_ERROR_CCU: json_data.get(PROXY_ERROR_CCU),
                PROXY_ERROR_IP: json_data.get(PROXY_ERROR_IP),
                PROXY_ERROR_CODE: json_data.get(PROXY_ERROR_CODE),
                PROXY_ERROR_MESSAGE: json_data.get(PROXY_ERROR_MESSAGE),
                PROXY_ERROR_TOTAL: json_data.get(PROXY_ERROR_TOTAL),
            },
        )
