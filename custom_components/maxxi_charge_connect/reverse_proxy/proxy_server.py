"""
Reverse-Proxy für MaxxiChargeConnect.

Der Proxy fängt Daten ab, die das Maxxigerät an maxxisun.app sendet, und gibt sie
an die Integration weiter. Optional werden die Daten auch an die echte Cloud weitergeleitet.
"""

import logging
import asyncio
import json
from typing import List, Optional
import dns.resolver
from aiohttp import web, ClientSession, ClientError

from homeassistant.helpers.storage import Store
from ..const import (
    PROXY_ERROR_EVENTNAME,
    PROXY_ERROR_DEVICE_ID,
    PROXY_ERROR_CODE,
    PROXY_ERROR_MESSAGE,
    PROXY_ERROR_TOTAL,
    PROXY_ERROR_CCU,
    PROXY_ERROR_IP,
    PROXY_FORWARDED,
    PROXY_PAYLOAD,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiProxyServer:
    """Reverse-Proxy für MaxxiCloud-Daten."""

    def __init__(self, hass, listen_port: int = 3001, enable_forward: bool = False):
        self.hass = hass
        self.listen_port = listen_port
        self.enable_forward_to_cloud = enable_forward
        self.runner: Optional[web.AppRunner] = None

        self._device_config_cache: dict[str, dict] = {}  # Cache pro deviceId
        self._store: Optional[Store] = None

    async def _init_storage(self):
        """Initialisiert Home Assistant persistent storage und lädt gespeicherte Config-Daten."""
        self._store = Store(self.hass, 1, f"{self.listen_port}_device_config.json")
        stored = await self._store.async_load()
        if stored:
            self._device_config_cache = stored
            _LOGGER.info("Geladene Config-Daten für Geräte: %s", list(stored.keys()))
        else:
            self._device_config_cache = {}

    async def fetch_cloud_config(self, device_id: str):
        """Ruft die originale Cloud einmalig ab und speichert die Daten in HA-Store."""
        ip = await self.resolve_external("maxxisun.app")
        cloud_url = f"http://{ip}:3001/config?deviceId={device_id}"
        try:
            async with ClientSession() as session:
                async with session.get(cloud_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._device_config_cache[device_id] = data
                        _LOGGER.info("Cloud-Daten für %s gespeichert", device_id)
                        # Persistieren
                        if self._store:
                            await self._store.async_save(self._device_config_cache)
                        return data
                    else:
                        _LOGGER.error(
                            "Cloud returned %s for device %s", resp.status, device_id
                        )
        except Exception as e:
            _LOGGER.error(
                "Fehler beim Abrufen der Cloud-Daten für %s: %s", device_id, e
            )
        return None

    async def _handle_config(self, request):
        """Antwortet mit gespeicherter Config oder ruft einmalig die Cloud ab (inkl. Refresh-Flag)."""
        device_id = request.query.get("deviceId")
        if not device_id:
            return web.Response(status=400, text="Missing deviceId")

        config_data = self._device_config_cache.get(device_id)
        refresh = False
        if config_data:
            # Prüfen, ob refresh_cloud_data gesetzt ist
            refresh = config_data.get("refresh_cloud_data", False)

        if not config_data or refresh:
            # Cloud einmalig abfragen
            config_data = await self.fetch_cloud_config(device_id)
            if config_data:
                # Flag zurücksetzen
                config_data["refresh_cloud_data"] = False
                self._device_config_cache[device_id] = config_data
                # Persistieren
                if self._store:
                    await self._store.async_save(self._device_config_cache)
            else:
                return web.Response(status=500, text="Cannot fetch config from cloud")

        headers = {
            "X-Powered-By": "Express",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Content-Length, Authorization, Accept,X-Requested-With",
            "Access-Control-Allow-Methods": "PUT,POST,GET,DELETE,OPTIONS",
        }

        return web.Response(
            text=json.dumps(config_data, ensure_ascii=False),
            headers=headers,
            content_type="application/json",
            charset="utf-8",
        )

    async def _handle_text(self, request):
        """Empfängt Daten vom Gerät."""
        try:
            data = await request.json()
        except Exception as e:
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        _LOGGER.debug("Proxy-Daten empfangen: %s", data)

        forwarded = await self._forward_to_cloud(data=data)

        # Event in Home Assistant feuern
        await self._on_reverse_proxy_message(data, forwarded)

        return web.Response(status=200, text="OK")

    async def _forward_to_cloud(self, data) -> bool:
        """Optional an Cloud weiterleiten."""
        forwarded = False
        if self.enable_forward_to_cloud:
            _LOGGER.debug("Cloud-Forwarding aktiv")
            try:
                ip = await self.resolve_external("maxxisun.app")
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

        return forwarded

    async def start(self):
        """Startet den Proxy und lädt gespeicherte Config-Daten."""
        await self._init_storage()
        app = web.Application()
        app["hass"] = self.hass
        app.router.add_post("/text", self._handle_text)
        app.router.add_get("/config", self._handle_config)

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

    async def resolve_external(
        self, domain: str, nameservers: Optional[List[str]] = None
    ) -> str:
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
