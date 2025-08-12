import logging
import asyncio
from typing import List

import dns.resolver

from aiohttp import web, ClientSession, ClientError

from  ..const import PROXY_ERROR_EVENTNAME, PROXY_ERROR_DEVICE_ID, \
                     PROXY_ERROR_CODE, PROXY_ERROR_MESSAGE, PROXY_ERROR_TOTAL, \
                     PROXY_ERROR_CCU, PROXY_ERROR_IP

_LOGGER = logging.getLogger(__name__)

class MaxxiProxyServer:
    def __init__(self, hass, listen_port=3001, enable_forward=False):
        self.hass = hass
        self.listen_port = listen_port        
        self.enable_forward_to_cloud = enable_forward
        self.runner = None

    async def _handle_text(self, request):
        try:
            data = await request.json()
        except Exception as e:
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        _LOGGER.warning("Lokaler Maxxi-Fehler empfangen: %s", data)

        # Beispiel: Aktuellen Fehler als HA-State speichern
        self.hass.states.async_set("maxxichargeconnect.last_error", str(data))
        await self._on_reverse_proxy_message(data)

        # An echte Cloud weiterleiten
        if self.enable_forward_to_cloud:
            _LOGGER.info("Forwarding to cloud is enabled")

            try:
                ip = await self.resolve_external("maxxisun1.app")
                _LOGGER.warning("maxxisun.app - ip = %s", ip)

                async with ClientSession() as session:
                    async with session.post(ip, json=data) as resp:
                        cloud_resp = await resp.text()
                        _LOGGER.info("Antwort der echten Cloud (%s): %s", ip, cloud_resp)

            except ClientError as e:
                _LOGGER.error(
                    "Cloud-Weiterleitung fehlgeschlagen: %s", e
                )
            except Exception as e:
                _LOGGER.error(
                    "Unerwarteter Fehler bei Cloud-Weiterleitung: %s", e
                )
        return web.Response(status=200, text="OK")

    async def start(self):
        app = web.Application()
        app["hass"] = self.hass
        app.router.add_post("/text", self._handle_text)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.listen_port)
        await site.start()

        _LOGGER.info("Maxxi-Proxy-Server gestartet auf Port %s", self.listen_port)

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            _LOGGER.info("Maxxi-Proxy-Server gestoppt")

    async def resolve_external(self, domain: str, nameservers: List[str] = ["8.8.8.8", "1.1.1.1"]) -> str:
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
            }
        )
