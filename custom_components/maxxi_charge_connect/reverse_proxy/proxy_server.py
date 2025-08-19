"""
Reverse-Proxy für MaxxiChargeConnect.

Der Proxy fängt Daten ab, die das Maxxi-Gerät an maxxisun.app sendet,
und gibt sie an die Integration weiter. Optional werden die Daten
auch an die originale Cloud weitergeleitet.
"""

import logging
import asyncio
import json
from typing import List, Optional, Callable
import dns.resolver
from aiohttp import web, ClientSession, ClientError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
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
    CONF_REFRESH_CONFIG_FROM_CLOUD,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    CONF_DEVICE_ID,
    DOMAIN,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiProxyServer:
    """Reverse-Proxy für MaxxiCloud-Daten."""

    def __init__(self, hass, listen_port: int = 3001):
        self.hass = hass
        self.listen_port = listen_port
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._device_config_cache: dict[str, dict] = {}  # Cache pro deviceId
        self._store: Optional[Store] = None

        # Dispatcher-Unsubscribe für jeden Webhook
        self._dispatcher_unsub: dict[str, Callable[[], None]] = {}

    async def _init_storage(self):
        self._store = Store(self.hass, 1, f"{self.listen_port}_device_config.json")
        stored = await self._store.async_load()
        if stored:
            self._device_config_cache = stored
            _LOGGER.info("Geladene Config-Daten für Geräte: %s", list(stored.keys()))
        else:
            self._device_config_cache = {}

    async def fetch_cloud_config(self, device_id: str):
        ip = await self.resolve_external("maxxisun.app")
        cloud_url = f"http://{ip}:3001/config?deviceId={device_id}"
        try:
            async with ClientSession() as session:
                async with session.get(cloud_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._device_config_cache[device_id] = data
                        _LOGGER.info("Cloud-Daten für %s gespeichert", device_id)
                        if self._store:
                            await self._store.async_save(self._device_config_cache)
                        return data
                    _LOGGER.error(
                        "Cloud returned %s for device %s", resp.status, device_id
                    )
        except Exception as e:
            _LOGGER.error(
                "Fehler beim Abrufen der Cloud-Daten für %s: %s", device_id, e
            )
        return None

    async def _handle_config(self, request):
        device_id = request.query.get(PROXY_ERROR_DEVICE_ID)
        if not device_id:
            return web.Response(status=400, text="Missing deviceId")

        entry = None
        enable_forward = False
        refresh_cloud = False
        for e in self.hass.config_entries.async_entries(DOMAIN):
            if e.data.get(CONF_DEVICE_ID) == device_id:
                entry = e
                enable_forward = e.data.get(
                    CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
                )
                refresh_cloud = e.data.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False)
                break

        if (
            refresh_cloud
            or enable_forward
            or device_id not in self._device_config_cache
        ):
            _LOGGER.info("Konfiguration wird von der Cloud gelesen für %s", device_id)
            config_data = await self.fetch_cloud_config(device_id)
            if not config_data:
                return web.Response(status=500, text="Cannot fetch config from cloud")
            if entry:
                data = dict(entry.data)
                data[CONF_REFRESH_CONFIG_FROM_CLOUD] = False
                await self.hass.config_entries.async_update_entry(entry, data=data)
        else:
            config_data = self._device_config_cache[device_id]
            _LOGGER.info("Konfiguration kommt aus dem Proxy Cache für %s", device_id)

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
        try:
            data = await request.json()
        except Exception as e:
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        _LOGGER.warning("Proxy-Daten empfangen: %s", data)
        device_id = data.get(CONF_DEVICE_ID)

        entry = None
        enable_forward = False
        for e in self.hass.config_entries.async_entries(DOMAIN):
            if e.data.get(CONF_DEVICE_ID) == device_id:
                entry = e
                enable_forward = e.data.get(
                    CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
                )
                break

        forwarded = await self._forward_to_cloud(data, enable_forward)
        await self._on_reverse_proxy_message(data, forwarded)
        return web.Response(status=200, text="OK")

    async def _forward_to_cloud(self, data, enable_forward: bool) -> bool:
        forwarded = False
        if enable_forward:
            try:
                ip = await self.resolve_external("maxxisun.app")
                async with ClientSession() as session:
                    async with session.post(f"http://{ip}", json=data) as resp:
                        await resp.text()
                forwarded = True
            except Exception as e:
                _LOGGER.error("Cloud-Forwarding Fehler: %s", e)
        return forwarded

    async def start(self):
        await self._init_storage()
        app = web.Application()
        app["hass"] = self.hass
        app.router.add_post("/text", self._handle_text)
        app.router.add_get("/config", self._handle_config)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", self.listen_port)
        await self.site.start()
        _LOGGER.info("Maxxi-Proxy-Server gestartet auf Port %s", self.listen_port)

    async def stop(self):
        for unsub in self._dispatcher_unsub.values():
            unsub()
        self._dispatcher_unsub.clear()

        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        _LOGGER.info("Maxxi-Proxy-Server gestoppt")

    async def resolve_external(
        self, domain: str, nameservers: Optional[List[str]] = None
    ) -> str:
        if nameservers is None:
            nameservers = ["8.8.8.8", "1.1.1.1"]
        loop = asyncio.get_running_loop()

        def blocking_resolve():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers
            return resolver.resolve(domain, "A")[0].to_text()

        return await loop.run_in_executor(None, blocking_resolve)

    def register_entry(self, entry):
        webhook_id = entry.data.get("webhook_id")
        if webhook_id and webhook_id not in self._dispatcher_unsub:
            signal = f"{DOMAIN}_{webhook_id}_update_sensor"
            unsub = async_dispatcher_connect(
                self.hass, signal, self._handle_webhook_signal
            )
            self._dispatcher_unsub[webhook_id] = unsub
            _LOGGER.info("Proxy hört auf Webhook: %s", webhook_id)

    def unregister_entry(self, entry):
        webhook_id = entry.data.get("webhook_id")
        unsub = self._dispatcher_unsub.pop(webhook_id, None)
        if unsub:
            unsub()
            _LOGGER.info("Proxy hört nicht mehr auf Webhook: %s", webhook_id)

    async def _handle_webhook_signal(self, data):
        device_id = data.get(PROXY_ERROR_DEVICE_ID)
        _LOGGER.debug("Proxy - Gerät (%s) Daten vom Webhook: %s", device_id, data)

        entry = next(
            (
                e
                for e in self.hass.config_entries.async_entries(DOMAIN)
                if e.data.get(CONF_DEVICE_ID) == device_id
            ),
            None,
        )
        enable_forward = (
            entry.data.get(
                CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
            )
            if entry
            else False
        )
        if enable_forward:
            _LOGGER.debug("Proxy - Gerät (%s) Daten an Cloud weiterleiten", device_id)
        else:
            _LOGGER.debug(
                "Proxy - Gerät (%s) Daten werden nicht weitergeben an Cloud weitergegeben",
                device_id,
            )

        # forwarded = await self._forward_to_cloud(data, enable_forward)
        # await self._on_reverse_proxy_message(data, forwarded)

    async def _on_reverse_proxy_message(self, json_data: dict, forwarded: bool):
        self.hass.bus.async_fire(
            PROXY_ERROR_EVENTNAME,
            {
                PROXY_ERROR_DEVICE_ID: json_data.get(PROXY_ERROR_DEVICE_ID),
                PROXY_ERROR_CCU: json_data.get(PROXY_ERROR_CCU),
                PROXY_ERROR_IP: json_data.get(PROXY_ERROR_IP),
                PROXY_ERROR_CODE: json_data.get(PROXY_ERROR_CODE),
                PROXY_ERROR_MESSAGE: json_data.get(PROXY_ERROR_MESSAGE),
                PROXY_ERROR_TOTAL: json_data.get(PROXY_ERROR_TOTAL),
                PROXY_PAYLOAD: json_data,
                PROXY_FORWARDED: forwarded,
            },
        )
