"""Reverse-Proxy für MaxxiChargeConnect.

Der Proxy fängt Daten ab, die das Maxxi-Gerät an maxxisun.app sendet,
oder als Webhook von Home Assistant, und gibt sie an die Integration weiter.
Optional werden die Daten auch an die originale Cloud weitergeleitet.
"""

import logging
from collections.abc import Callable
from ipaddress import ip_address

import dns.resolver
from aiohttp import ClientConnectorError, ClientSession, ClientTimeout, web
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.storage import Store

from ..const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_REFRESH_CONFIG_FROM_CLOUD,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DOMAIN,
    ERRORS,
    MAXXISUN_CLOUD_URL,
    PROXY_ERROR_CCU,
    PROXY_ERROR_DEVICE_ID,
    WEBHOOK_SIGNAL_UPDATE,
)
from ..tools import fire_status_event
from ..webhook import record_v1_telemetry

_LOGGER = logging.getLogger(__name__)


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

        try:
            ip = await self.resolve_external(MAXXISUN_CLOUD_URL)
            cloud_url = f"http://{ip}:3001/config"
            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(cloud_url, params={PROXY_ERROR_DEVICE_ID: device_id}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._device_config_cache[device_id] = data
                        _LOGGER.debug("Cloud-Daten für %s gespeichert", device_id)
                        if self._store:
                            await self._store.async_save(self._device_config_cache)
                        return data
                    _LOGGER.error("Cloud returned %s for device %s", resp.status, device_id)
        except ClientConnectorError as e:
            _LOGGER.error("DNS/Verbindungsproblem mit Cloud (%s, %s, %s)", device_id, cloud_url, e)
        except TimeoutError:
            _LOGGER.error(
                "Timeout beim Abholen der Konfiguration aus der Cloud (%s)",
                device_id,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception(
                "Unerwarteter Fehler beim Abholen der Konfiguration aus der Cloud (%s)",
                device_id,
            )
        return None

    def _get_authorized_entry(self, request: web.Request, device_id: str) -> ConfigEntry | None:
        """Return the matching CCU entry only for an authorized request.

        A request is authorized when the device ID belongs to a configured
        CCU with the local cloud proxy enabled and the request originates
        from that CCU's configured IP address.

        The remote address is obtained from the underlying TCP connection,
        not from client-controlled forwarding headers.

        Args:
            request: Incoming HTTP request.
            device_id: Device identifier provided by the requesting CCU.

        Returns:
            The matching configuration entry or None if access is denied.

        """
        if not isinstance(device_id, str) or not device_id:
            return None

        transport = request.transport
        if transport is None:
            return None

        peer = transport.get_extra_info("peername")
        if not peer:
            return None

        try:
            remote_ip = ip_address(peer[0])
        except (ValueError, TypeError):
            return None

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.state is not ConfigEntryState.LOADED or entry.data.get(CONF_DEVICE_ID) != device_id:
                continue

            if not entry.data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False):
                continue

            configured_ip = entry.data.get(CONF_IP_ADDRESS)
            if not configured_ip:
                continue

            try:
                allowed_ip = ip_address(configured_ip)
            except ValueError:
                continue

            if remote_ip == allowed_ip:
                return entry

        return None

    async def _handle_config(self, request):
        device_id = request.query.get(PROXY_ERROR_DEVICE_ID)
        if not device_id:
            return web.Response(status=400, text="Missing deviceId")

        entry = self._get_authorized_entry(request, device_id)

        if entry is None:
            _LOGGER.warning("Unberechtigte Proxy-Konfigurationsanfrage abgelehnt")
            return web.Response(status=403, text="Forbidden")

        enable_forward = entry.data.get(
            CONF_ENABLE_FORWARD_TO_CLOUD,
            DEFAULT_ENABLE_FORWARD_TO_CLOUD,
        )
        refresh_cloud = entry.data.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False)

        if refresh_cloud or enable_forward or device_id not in self._device_config_cache:
            _LOGGER.debug("Konfiguration wird von der Cloud gelesen für %s", device_id)
            config_data = await self.fetch_cloud_config(device_id)
            if self._get_authorized_entry(request, device_id) is not entry:
                return web.Response(status=403, text="Forbidden")
            if not config_data:
                return web.Response(status=500, text="Cannot fetch config from cloud")
            if refresh_cloud and entry.data.get(CONF_REFRESH_CONFIG_FROM_CLOUD):
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_REFRESH_CONFIG_FROM_CLOUD: False}
                )
        else:
            config_data = self._device_config_cache[device_id]
            _LOGGER.debug("Konfiguration kommt aus dem Proxy Cache für %s", device_id)

        return web.json_response(config_data)

    async def _handle_text(self, request):
        """Accept and optionally forward data from an authorized CCU."""
        try:
            data = await request.json()
        except ValueError:
            _LOGGER.debug("Ungültige JSON-Daten empfangen")
            return web.Response(status=400, text="Invalid JSON")

        if not isinstance(data, dict):
            return web.Response(status=400, text="Invalid JSON structure")

        device_id = data.get(PROXY_ERROR_DEVICE_ID)
        if device_id == ERRORS:
            device_id = data.get(PROXY_ERROR_CCU)
        if not isinstance(device_id, str) or not device_id:
            return web.Response(status=400, text="Missing deviceId")

        entry = self._get_authorized_entry(request, device_id)
        if entry is None:
            _LOGGER.warning("Unberechtigte Proxy-Datenanfrage abgelehnt")
            return web.Response(status=403, text="Forbidden")

        enable_forward = entry.data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)
        enable_cloud_data = entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

        try:
            forwarded = await self._forward_to_cloud(device_id, enable_cloud_data, data, enable_forward)
            if self._get_authorized_entry(request, device_id) is not entry:
                return web.Response(status=403, text="Forbidden")
            if enable_cloud_data and data[PROXY_ERROR_DEVICE_ID] != ERRORS:
                record_v1_telemetry(self.hass, entry)
            await self._on_reverse_proxy_message(data, forwarded)
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Fehler bei der Verarbeitung der Proxy-Daten")
            return web.Response(status=500, text="An internal error has occurred")

        return web.Response(status=200, text="OK")

    async def _forward_to_cloud(self, device_id, enable_cloud_data: bool, data, enable_forward: bool) -> bool:
        forwarded = False

        if enable_forward:
            url = f"http://{MAXXISUN_CLOUD_URL}:3001/text"
            try:
                if enable_cloud_data:
                    # Externe Auflösung erzwingen
                    ip = await self.resolve_external(MAXXISUN_CLOUD_URL)
                    url = f"http://{ip}:3001/text"

                _LOGGER.debug("Sende Daten an maxxisun.app (%s)", url)

                headers = {
                    "Host": MAXXISUN_CLOUD_URL,  # wichtig für SNI und TLS
                    "Content-Type": "application/json",
                }

                # 3. POST absenden
                timeout = ClientTimeout(total=10)
                async with ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=data) as resp:
                        if resp.status == 200:
                            forwarded = True
                            _LOGGER.debug(
                                "Daten erfolgreich an Cloud verschickt (%s)",
                                resp.status,
                            )
                        else:
                            _LOGGER.error(
                                "Daten konnten nicht an die Cloud geschickt werden (%s)",
                                resp.status,
                            )
            except ClientConnectorError as e:
                _LOGGER.error(
                    "DNS/Verbindungsproblem beim Senden an Cloud (%s, %s, %s)",
                    device_id,
                    url,
                    e,
                )
            except TimeoutError:
                _LOGGER.error("Timeout beim Senden an Cloud(%s, %s)", device_id, url)
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.exception(
                    "Unerwarteter Fehler beim Cloud-Forwarding an (%s, %s, %s)",
                    device_id,
                    url,
                    e,
                )

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

    async def resolve_external(self, domain: str, nameservers: list[str] | None = None) -> str:
        """Ermittelt die IP der Cloud über einen externen Nameserver."""

        if nameservers is None:
            nameservers = ["8.8.8.8", "1.1.1.1"]

        def blocking_resolve():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers
            return resolver.resolve(domain, "A")[0].to_text()

        return await self.hass.async_add_executor_job(blocking_resolve)

    @property
    def has_entries(self) -> bool:
        """Return whether any CCU uses the proxy."""
        return bool(self._dispatcher_unsub)

    def register_entry(self, entry: ConfigEntry) -> None:
        """Subscribe to the entry's webhook telemetry."""
        if entry.entry_id in self._dispatcher_unsub:
            return

        signal = self.hass.data[DOMAIN][entry.entry_id][WEBHOOK_SIGNAL_UPDATE]

        async def _handler(data):
            await self._handle_webhook_signal(data, entry)

        self._dispatcher_unsub[entry.entry_id] = async_dispatcher_connect(self.hass, signal, _handler)
        _LOGGER.info("Proxy hört auf Webhook")

    def unregister_entry(self, entry: ConfigEntry) -> None:
        """Unsubscribe from the entry's webhook telemetry."""
        unsub = self._dispatcher_unsub.pop(entry.entry_id, None)
        if unsub:
            unsub()
            _LOGGER.info("Proxy hört nicht mehr auf Webhook")

    async def _handle_webhook_signal(self, data: dict, entry: ConfigEntry) -> None:
        if entry.entry_id not in self._dispatcher_unsub:
            return

        device_id = entry.data.get(CONF_DEVICE_ID)
        enable_forward = entry.data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)
        enable_cloud_data = entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

        forwarded = await self._forward_to_cloud(device_id, enable_cloud_data, data, enable_forward)
        await self._on_reverse_proxy_message(data, forwarded)

    async def _on_reverse_proxy_message(self, json_data: dict, forwarded: bool):
        await fire_status_event(self.hass, json_data, forwarded)
