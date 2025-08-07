import logging
from aiohttp import web, ClientSession

_LOGGER = logging.getLogger(__name__)

class MaxxiProxyServer:
    def __init__(self, hass, listen_port=3001, forward_url=None):
        self.hass = hass
        self.listen_port = listen_port
        self.forward_url = forward_url
        self.runner = None

    async def _handle_text(self, request):
        try:
            data = await request.json()
            _LOGGER.info("Lokaler Maxxi-Fehler empfangen: %s", data)

            # Beispiel: Aktuellen Fehler als HA-State speichern
            self.hass.states.async_set("maxxichargeconnect.last_error", str(data))

            # An echte Cloud weiterleiten
            if self.forward_url:
                async with ClientSession() as session:
                    async with session.post(self.forward_url, json=data) as resp:
                        cloud_resp = await resp.text()
                        _LOGGER.info("Antwort der echten Cloud (%s): %s", self.forward_url, cloud_resp)
            else:
                _LOGGER.warning("Keine Weiterleitungs-URL gesetzt. Cloud-Forwarding übersprungen.")

            return web.Response(text="OK")

        except Exception as e:
            _LOGGER.exception("Fehler im Maxxi-Proxy-Server: %s", e)
            return web.Response(status=500, text="Interner Fehler")

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
