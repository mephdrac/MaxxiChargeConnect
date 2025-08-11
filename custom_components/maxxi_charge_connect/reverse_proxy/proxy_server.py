import logging
from aiohttp import web, ClientSession, ClientError

_LOGGER = logging.getLogger(__name__)

class MaxxiProxyServer:
    def __init__(self, hass, listen_port=3001, enable_forward=False, forward_url=None):
        self.hass = hass
        self.listen_port = listen_port
        self.forward_url = forward_url
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

        # An echte Cloud weiterleiten
        if self.enable_forward_to_cloud:
            _LOGGER.info("Forwarding to cloud is enabled")

            if self.forward_url:

                try:
                    async with ClientSession() as session:
                        async with session.post(self.forward_url, json=data) as resp:
                            cloud_resp = await resp.text()
                            _LOGGER.info("Antwort der echten Cloud (%s): %s", self.forward_url, cloud_resp)
                except ClientError as e:
                    _LOGGER.error(
                        "Cloud-Weiterleitung fehlgeschlagen: %s", e
                    )
                except Exception as e:
                    _LOGGER.error(
                        "Unerwarteter Fehler bei Cloud-Weiterleitung: %s", e
                    )
            else:
                _LOGGER.error("Keine Weiterleitungs-URL gesetzt")

        # Dem Maxxi-Gerät antworten, auch wenn Cloud weg ist
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
