"""
Reverse-Proxy für MaxxiChargeConnect.

Der Proxy fängt Daten ab, die das Maxxigerät an maxxisun.app sendet, und gibt sie
an die Integration weiter. Optional werden die Daten auch an die echte Cloud weitergeleitet.
"""

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
    PROXY_FORWARDED,
    PROXY_PAYLOAD
)

_LOGGER = logging.getLogger(__name__)


class MaxxiProxyServer:
    """Reverse-Proxy für MaxxiCloud-Daten."""

    def __init__(self, hass, listen_port: int = 3001, enable_forward: bool = False):
        self.hass = hass
        self.listen_port = listen_port
        self.enable_forward_to_cloud = enable_forward
        self.runner: Optional[web.AppRunner] = None

    async def _handle_text(self, request):
        """Empfängt Daten vom Gerät."""
        try:
            data = await request.json()
        except Exception as e:
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        _LOGGER.warning("Proxy-Daten empfangen: %s", data)

        # Optional an Cloud weiterleiten
        forwarded = False
        if self.enable_forward_to_cloud:
            _LOGGER.debug("Cloud-Forwarding aktiv")
            try:
                ip = await self.resolve_external("maxxisun1.app")
                _LOGGER.debug("maxxisun.app - IP = %s", ip)

                async with ClientSession() as session:
                    async with session.post(f"http://{ip}", json=data) as resp:
                        cloud_resp = await resp.text()
                        _LOGGER.debug("Antwort der echten Cloud: %s", cloud_resp)
                forwarded = True
            except ClientError as e:
                _LOGGER.error("Cloud-Forwarding fehlgeschlagen: %s", e)
            except Exception as e:
                _LOGGER.error("Unerwarteter Fehler beim Cloud-Forwarding: %s", e)

        # Event in Home Assistant feuern
        await self._on_reverse_proxy_message(data, forwarded)

        return web.Response(status=200, text="OK")

    async def start(self):
        """Startet den Proxy."""
        app = web.Application()
        app["hass"] = self.hass
        app.router.add_post("/text", self._handle_text)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.listen_port)
        await site.start()

        _LOGGER.info("Maxxi-Proxy-Server gestartet auf Port %s", self.listen_port)

    async def stop(self):
        """Stoppt den Proxy."""
        if self.runner:
            await self.runner.cleanup()
            _LOGGER.info("Maxxi-Proxy-Server gestoppt")

    async def resolve_external(self, domain: str, nameservers: Optional[List[str]] = None) -> str:
        """Löst die echte Cloud-Adresse auf."""
        if nameservers is None:
            nameservers = ["8.8.8.8", "1.1.1.1"]

        loop = asyncio.get_running_loop()

        def blocking_resolve():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers
            answers = resolver.resolve(domain, "A")
            return answers[0].to_text()

        ip = await loop.run_in_executor(None, blocking_resolve)
        return ip

    async def _on_reverse_proxy_message(self, json_data: dict, forwarded: bool):
        """Feuert ein HA-Event für die Sensoren."""
        self.hass.bus.async_fire(
            PROXY_ERROR_EVENTNAME,
            {
                PROXY_ERROR_DEVICE_ID: json_data.get(PROXY_ERROR_DEVICE_ID),
                PROXY_ERROR_CCU: json_data.get(PROXY_ERROR_CCU),
                PROXY_ERROR_IP: json_data.get(PROXY_ERROR_IP),
                PROXY_ERROR_CODE: json_data.get(PROXY_ERROR_CODE),
                PROXY_ERROR_MESSAGE: json_data.get(PROXY_ERROR_MESSAGE),
                PROXY_ERROR_TOTAL: json_data.get(PROXY_ERROR_TOTAL),
                PROXY_PAYLOAD: json_data,  # voller Payload für Sensoren
                PROXY_FORWARDED: forwarded,
            },
        )
