"""Reverse-Proxy für MaxxiChargeConnect.

Der Proxy fängt Daten ab, die das Maxxi-Gerät an maxxisun.app sendet,
oder als Webhook von Home Assistant, und gibt sie an die Integration weiter.
Optional werden die Daten auch an die originale Cloud weitergeleitet.
"""

import asyncio
from collections.abc import Callable
import json
import logging
import time

from aiohttp import ClientSession, web
import dns.resolver

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_IP_ADDRESS, CONF_WEBHOOK_ID
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.storage import Store

from ..tools import fire_status_event

from ..const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    CONF_REFRESH_CONFIG_FROM_CLOUD,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DOMAIN,
    MAXXISUN_CLOUD_URL,
    PROXY_ERROR_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

# Interner Zähler für sendCount pro Gerät
_send_counters: dict[str, int] = {}
_start_times: dict[str, float] = {}


def webhook_to_cloud_format(webhook_data: dict, ip_addr: str) -> dict:
    """Erstellt aus den Webhook-Daten einen Datensatz für die Cloud."""
    device_id = webhook_data.get("deviceId")
    if not device_id:
        raise ValueError("deviceId fehlt im Webhook")

    # sendCount hochzählen
    count = _send_counters.get(device_id, 0) + 1
    _send_counters[device_id] = count

    # Standardwerte für converter/box
    converters_info = [
        {
            "ccuTemperature": 29,
            "ccuVoltage": 0,
            "ccuCurrent": 0,
            "ccuPower": 0,
            "version": "106",
            "command": "81 10 0 0 0 2 4 11 94 0 0 1e bd",
        },
        {
            "ccuTemperature": 29,
            "ccuVoltage": 0,
            "ccuCurrent": 0,
            "ccuPower": 0,
            "version": "106",
            "command": "82 10 0 0 0 2 4 11 94 0 0 11 f9",
        },
    ]

    # BatteriesInfo berechnen
    batteries_info = []
    for b in webhook_data.get("batteriesInfo", []):
        voltage = b.get("batteryVoltage", 0)
        current = b.get("batteryCurrent", 0)
        power = (voltage * current) / 1000 if voltage and current else 0
        soc = b.get("batterySOC", webhook_data.get("SOC", 0))
        nominal_capacity = b.get("batteryNominalCapacity", b.get("batteryCapacity", 0))
        batteries_info.append(
            {
                "batteryVoltage": voltage,
                "batteryCurrent": current,
                "batteryPower": power,
                "batterySOC": soc,
                "batteryNominalCapacity": nominal_capacity,
                "batteryCapacity": b.get("batteryCapacity", 0),
                "pvVoltage": b.get("pvVoltage", 0),
                "pvCurrent": b.get("pvCurrent", 0),
                "pvPower": (b.get("pvVoltage", 0) * b.get("pvCurrent", 0)) / 1000
                if b.get("pvVoltage") and b.get("pvCurrent")
                else 0,
                "mpptVoltage": b.get("mpptVoltage", 0),
                "mpptCurrent": b.get("mpptCurrent", 0),
                "mpptPower": (b.get("mpptVoltage", 0) * b.get("mpptCurrent", 0)) / 1000
                if b.get("mpptVoltage") and b.get("mpptCurrent")
                else 0,
            }
        )

    # Startzeit für uptime speichern
    if f"{device_id}_start_time" not in _start_times:
        _start_times[f"{device_id}_start_time"] = time.time()
    uptime = int(time.time() - _start_times[f"{device_id}_start_time"])

    return {
        "deviceId": device_id,
        "ip_addr": ip_addr,
        "wifiStrength": webhook_data.get("wifiStrength", -50),
        "meterWifiStrength": webhook_data.get("meterWifiStrength", -50),
        "sendCount": count,
        "Pr": webhook_data.get("Pr", 0),
        "meterReading": "",
        "PV_power_total": webhook_data.get("PV_power_total", 0),
        "SOC": webhook_data.get("SOC", 0),
        "batteriesInfo": batteries_info,
        "v_ccu": 0,
        "i_ccu": 0,
        "ccuTotalPower": 0,
        "microCurve": 99,
        "convertersInfo": converters_info,
        "Pccu": webhook_data.get("Pccu", 0),
        "error": 0,
        "firmwareVersion": webhook_data.get("firmwareVersion", 0),
        "box_id": "U2hlbGx5IFBybw",
        "uptime": uptime,
    }


class MaxxiProxyServer:
    """Reverse-Proxy für MaxxiCloud-Daten."""

    def __init__(self, hass: HomeAssistant, listen_port: int = 3001) -> None:
        """Konstruktor vom Reverse-Proxy."""
        self.hass = hass
        self.listen_port = listen_port
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._device_config_cache: dict[str, dict] = {}  # Cache pro deviceId
        self._store: Store | None = None
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
        """Holt die Konfiguration direkt von der Cloud."""

        ip = await self.resolve_external("maxxisun.app")
        cloud_url = f"http://{ip}:3001/config?deviceId={device_id}"
        try:
            async with ClientSession() as session:
                async with session.get(cloud_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._device_config_cache[device_id] = data
                        _LOGGER.debug("Cloud-Daten für %s gespeichert", device_id)
                        if self._store:
                            await self._store.async_save(self._device_config_cache)
                        return data
                    _LOGGER.error(
                        "Cloud returned %s for device %s", resp.status, device_id
                    )
        except Exception as e:  # pylint: disable=broad-exception-caught
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
            _LOGGER.debug("Konfiguration wird von der Cloud gelesen für %s", device_id)
            config_data = await self.fetch_cloud_config(device_id)
            if not config_data:
                return web.Response(status=500, text="Cannot fetch config from cloud")
            if entry:
                data = dict(entry.data)
                data[CONF_REFRESH_CONFIG_FROM_CLOUD] = False
                self.hass.config_entries.async_update_entry(entry, data=data)
        else:
            config_data = self._device_config_cache[device_id]
            _LOGGER.debug("Konfiguration kommt aus dem Proxy Cache für %s", device_id)

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
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Ungültige JSON-Daten empfangen: %s", e)
            return web.Response(status=400, text="Invalid JSON")

        device_id = data.get(CONF_DEVICE_ID)
        _LOGGER.debug("Proxy-Daten empfangen: %s", data)

        # Entscheiden, ob Transformation nötig ist

        try:
            entry = None
            ip_addr = ""
            enable_forward = False

            for cur_entry in self.hass.config_entries.async_entries(DOMAIN):
                if cur_entry.data.get(CONF_DEVICE_ID) == device_id:
                    entry = cur_entry
                    enable_forward = cur_entry.data.get(
                        CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
                    )
                    ip_addr = entry.data.get(CONF_IP_ADDRESS, "") if entry else ""
                    break

            if "ip_addr" not in data:
                cloud_data = webhook_to_cloud_format(data, ip_addr)
            else:
                cloud_data = data

            forwarded = await self._forward_to_cloud(cloud_data, enable_forward)
            await self._on_reverse_proxy_message(cloud_data, forwarded)
            return web.Response(status=200, text="OK")

        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Error (%s)", e)
            return web.Response(status=400, text="An internal error has occurred")

    async def _forward_to_cloud(self, data, enable_forward: bool) -> bool:
        forwarded = False

        if enable_forward:
            _LOGGER.debug("Leite an Cloud (%s)", data)

            try:
                ip = await self.resolve_external(MAXXISUN_CLOUD_URL)
                url = f"http://{ip}:3001/text"

                _LOGGER.debug("Sende Daten an maxxisun.app (%s)", ip)

                headers = {
                    "Host": MAXXISUN_CLOUD_URL,  # wichtig für SNI und TLS
                    "Content-Type": "application/json",
                }

                # 3. POST absenden
                async with ClientSession() as session:
                    async with session.post(url, headers=headers, json=data) as resp:
                        text = await resp.text()

                        if resp.status == 200:
                            forwarded = True
                            _LOGGER.debug(
                                "Daten erfolgreich an Cloud verschickt - (%s): %s",
                                resp.status,
                                text,
                            )
                        else:
                            _LOGGER.error(
                                "Daten konnte nicht an die Cloud geschickt werden: %s - %s",
                                resp.status,
                                text,
                            )
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error("Cloud-Forwarding Fehler: %s", e)
        return forwarded

    async def start(self):
        """Startet den Reverse-Proxy."""

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
        """Stoppt den Proxy-Server."""
        for unsub in self._dispatcher_unsub.values():
            unsub()
        self._dispatcher_unsub.clear()

        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        _LOGGER.info("Maxxi-Proxy-Server gestoppt")

    async def resolve_external(
        self, domain: str, nameservers: list[str] | None = None
    ) -> str:
        """Ermittelt die IP der Cloud über einen externen Nameserver."""

        if nameservers is None:
            nameservers = ["8.8.8.8", "1.1.1.1"]
        loop = asyncio.get_running_loop()

        def blocking_resolve():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers
            return resolver.resolve(domain, "A")[0].to_text()

        return await loop.run_in_executor(None, blocking_resolve)

    def register_entry(self, entry):
        """Registriert einen Entry für den Proxy-Server."""

        webhook_id = entry.data.get(CONF_WEBHOOK_ID)
        if webhook_id and webhook_id not in self._dispatcher_unsub:
            signal = f"{DOMAIN}_{webhook_id}_update_sensor"
            unsub = async_dispatcher_connect(
                self.hass, signal, self._handle_webhook_signal
            )
            self._dispatcher_unsub[webhook_id] = unsub
            _LOGGER.info("Proxy hört auf Webhook: %s", webhook_id)

    def unregister_entry(self, entry):
        """Dregistriert einen Entry für den Proxy-Server."""

        webhook_id = entry.data.get(CONF_WEBHOOK_ID)
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

        if "ip_addr" not in data:
            ip_addr = entry.data.get(CONF_IP_ADDRESS, "") if entry else ""
            cloud_data = webhook_to_cloud_format(data, ip_addr)
        else:
            cloud_data = data

        await self._forward_to_cloud(cloud_data, enable_forward)
        # await self._on_reverse_proxy_message(cloud_data, forwarded)

    async def _on_reverse_proxy_message(self, json_data: dict, forwarded: bool):
        await fire_status_event(self.hass, json_data, forwarded)
        # self.hass.bus.async_fire(
        #     PROXY_STATUS_EVENTNAME,
        #     {
        #         PROXY_ERROR_DEVICE_ID: json_data.get(PROXY_ERROR_DEVICE_ID),
        #         PROXY_ERROR_CCU: json_data.get(PROXY_ERROR_CCU),
        #         PROXY_ERROR_IP: json_data.get(PROXY_ERROR_IP),
        #         PROXY_ERROR_CODE: json_data.get(PROXY_ERROR_CODE),
        #         PROXY_ERROR_MESSAGE: json_data.get(PROXY_ERROR_MESSAGE),
        #         PROXY_ERROR_TOTAL: json_data.get(PROXY_ERROR_TOTAL),
        #         PROXY_PAYLOAD: json_data,
        #         PROXY_FORWARDED: forwarded,
        #     },
        # )
