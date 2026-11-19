"""CCU V1 telemetry through webhook-server"""

import asyncio
import logging

from homeassistant.const import Platform
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from ..const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_SUMMER_MIN_CHARGE,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MODE,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    DEFAULT_SUMMER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MODE,
    DOMAIN,
)
from ..http_scan.maxxi_data_update_coordinator import CCU_V1_HTTP_SCAN_FIELDS, MaxxiDataUpdateCoordinator
from ..reverse_proxy.proxy_server import MaxxiProxyServer
from ..webhook import async_register_webhook, async_unregister_webhook
from .ccu_base_connection import CcuBaseConnection

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


class CCCv1Connection(CcuBaseConnection):
    """Route only this CCU's telemetry to its sensor dispatcher."""

    async def async_setup(self) -> None:
        raise NotImplementedError

    # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    async def async_setup_entry(self) -> bool:
        """Initialisiert eine neue Instanz der Integration beim Hinzufügen über die UI."""
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN].setdefault(self.entry.entry_id, {})

        # Restore operating settings for this CCU from its configuration entry.
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]

        entry_data[CONF_WINTER_MODE] = self.entry.options.get(
            CONF_WINTER_MODE,
            DEFAULT_WINTER_MODE,
        )

        entry_data[CONF_SUMMER_MIN_CHARGE] = self.entry.options.get(
            CONF_SUMMER_MIN_CHARGE,
            DEFAULT_SUMMER_MIN_CHARGE,
        )

        entry_data[CONF_WINTER_MIN_CHARGE] = self.entry.options.get(
            CONF_WINTER_MIN_CHARGE,
            DEFAULT_WINTER_MIN_CHARGE,
        )

        entry_data[CONF_WINTER_MAX_CHARGE] = self.entry.options.get(
            CONF_WINTER_MAX_CHARGE,
            DEFAULT_WINTER_MAX_CHARGE,
        )

        coordinator = MaxxiDataUpdateCoordinator(self.hass, self.entry, CCU_V1_HTTP_SCAN_FIELDS)

        self.hass.data[DOMAIN][self.entry.entry_id]["coordinator"] = coordinator
        await coordinator.async_config_entry_first_refresh()

        # Webhook registrieren
        await async_register_webhook(self.hass, self.entry)

        try:
            # Plattformen laden
            await self.hass.config_entries.async_forward_entry_setups(self.entry, PLATFORMS)

        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Laden der Plattformen: %s", e)
            return False

        if self.entry.data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY):
            domain_data = self.hass.data[DOMAIN]
            async with domain_data.setdefault("proxy_lock", asyncio.Lock()):
                proxy = domain_data["proxy"]
                if proxy is None:
                    proxy = MaxxiProxyServer(self.hass)
                    try:
                        await proxy.start()
                    except OSError as err:
                        await proxy.stop()
                        _LOGGER.error("Fehler beim Starten des Proxy-Servers: %s", err)
                        proxy = None
                    domain_data["proxy"] = proxy

                if proxy is not None:
                    proxy.register_entry(self.entry)

        try:
            # Device-ID prüfen
            await self.check_device_id_issue()
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Prüfen der Device ID: %s", e)

        return True

    async def async_unload(self) -> None:
        """Entlädt die Integration vollständig und deregistriert den Webhook."""

        await async_unregister_webhook(self.hass, self.entry)

        domain_data = self.hass.data[DOMAIN]
        async with domain_data.setdefault("proxy_lock", asyncio.Lock()):
            proxy = domain_data["proxy"]
            if proxy is not None:
                proxy.unregister_entry(self.entry)
                if not proxy.has_entries:
                    await proxy.stop()
                    domain_data["proxy"] = None

    async def check_device_id_issue(self) -> None:
        """Prüfen, ob die Device ID gesetzt wurde."""
        entry_id = self.entry.entry_id
        if not self.entry.data.get(CONF_DEVICE_ID):
            _LOGGER.error("Device-ID fehlt für Entry %s (%s)", entry_id, self.entry.title)
            async_create_issue(
                self.hass,
                DOMAIN,
                f"missing_device_id_{entry_id}",
                is_fixable=False,
                severity=IssueSeverity.CRITICAL,
                issue_domain=DOMAIN,
                translation_key="missing_device_id",
                translation_placeholders={"entry_title": self.entry.title},
            )
        else:
            async_delete_issue(self.hass, DOMAIN, f"missing_device_id_{entry_id}")
