import logging

# from homeassistant.core import HomeAssistant
# from homeassistant.config_entries import ConfigEntry

from .ccu_base_connection import CcuBaseConnection
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
    CONF_WINTER_MODE,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    DEFAULT_SUMMER_MIN_CHARGE,
    DEFAULT_WINTER_MODE,
    DOMAIN,
    NEIN,
    # NOTIFY_MIGRATION,
    OPTIONAL,
    REQUIRED,
)

from ..http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator
# from ..migration.migration_from_yaml import MigrateFromYaml
from ..reverse_proxy.proxy_server import MaxxiProxyServer
from ..webhook import async_register_webhook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


class ccuV1Connection(CcuBaseConnection):

    # def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
    #     super().__init__(hass, entry)

    async def async_setup(self) -> None:
        raise NotImplementedError    

    # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    async def async_setup_entry(self) -> bool:
        """Initialisiert eine neue Instanz der Integration beim Hinzufügen über die UI."""
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][self.entry.entry_id] = {}

        sensor_list = [
            ("PowerMeterIp", "Messgerät IP:", REQUIRED),
            ("PowerMeterType", "Messgerät Typ:", REQUIRED),
            ("MaximumPower", "Maximale Leistung:", REQUIRED),
            ("OfflineOutputPower", "Offline-Ausgangsleistung:", REQUIRED),
            ("NumberOfBatteries", "Batterien im System:", REQUIRED),
            ("OutputOffset", "Ausgabe korrigieren:", REQUIRED),
            ("CcuSpeed", "CCU-Geschwindigkeit:", REQUIRED),
            ("Microinverter", "Mikro-Wechselrichter-Typ:", REQUIRED),
            ("ResponseTolerance", "Reaktionstoleranz:", REQUIRED),
            ("MinimumBatteryDischarge", "Minimale Entladung der Batterie:", REQUIRED),
            ("MaximumBatteryCharge", "Maximale Akkuladung:", REQUIRED),
            ("DC/DC-Algorithmus", "DC/DC-Algorithmus:", REQUIRED),
            ("Cloudservice", "Cloudservice:", REQUIRED),
            ("LocalServer", "Lokalen Server nutzen:", NEIN),
            ("APIRoute", "API-Route:", OPTIONAL),
        ]

        # Initiale Werte für Winter- und Sommerbetrieb setzen
        winter_mode = self.entry.options.get(
            CONF_WINTER_MODE,
            DEFAULT_WINTER_MODE,
        )

        summer_min_discharge = self.entry.options.get(CONF_SUMMER_MIN_CHARGE, DEFAULT_SUMMER_MIN_CHARGE)

        self.hass.data[DOMAIN][CONF_WINTER_MODE] = winter_mode
        self.hass.data[DOMAIN][CONF_SUMMER_MIN_CHARGE] = summer_min_discharge

        coordinator = MaxxiDataUpdateCoordinator(self.hass, self.entry, sensor_list)

        self.hass.data[DOMAIN][self.entry.entry_id]["coordinator"] = coordinator
        await coordinator.async_config_entry_first_refresh()

        # Webhook registrieren
        await async_register_webhook(self.hass, self.entry)

        try:
            # Plattformen laden
            await self.hass.config_entries.async_forward_entry_setups(self. entry, PLATFORMS)

        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Laden der Plattformen: %s", e)
            return False

        # # Migration von YAML-Konfiguration
        # migrator = MigrateFromYaml(self.hass, self.entry)
    
        # async def handle_trigger_migration(call):
        #     mappings = call.data.get("mappings", [])
    
        #     try:
        #         if not isinstance(mappings, list) or not all(isinstance(item, dict) for item in mappings):
        #             raise ValueError("Mappings must be a list of dictionaries.")
        #         for item in mappings:
        #             if "old_sensor" not in item or "new_sensor" not in item:
        #                 raise ValueError("Each mapping must contain 'old_sensor' and 'new_sensor'.")
        #     except ValueError as e:
        #         _LOGGER.error("Invalid mappings provided for migration: %s", e)
        #         return
    
        #     try:
        #         await migrator.async_handle_trigger_migration(mappings)
        #     except Exception as e:  # pylint: disable=broad-exception-caught
        #         _LOGGER.error("Fehler bei der Migration: %s", e)
    
        # hass.services.async_register(DOMAIN, "migration_von_yaml_konfiguration", handle_trigger_migration)
    
        # # Migration-Hinweis
        # notify_migration = entry.data.get(NOTIFY_MIGRATION, False)
        # if notify_migration:
    
        #     async def sub_notify_migration():
        #         try:
        #             await asyncio.sleep(10)  # Warte 10 Sekunden nach Start
        #             await migrator.async_notify_possible_migration()
        #         except Exception as e:  # pylint: disable=broad-exception-caught
        #             _LOGGER.error("Fehler beim Migration-Hinweis: %s", e)
    
        #     task = hass.async_create_task(sub_notify_migration())
        #     task.add_done_callback(
        #         lambda t: _LOGGER.error("Notify-Migration-Task beendet: %s", t.exception()) if t.exception() else None
        #     )
    
        # --- GLOBALEN PROXY starten ---
        proxy_enabled = self.entry.data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY)
        if proxy_enabled:
            if self.hass.data[DOMAIN]["proxy"] is None:
                _LOGGER.info("Starte globalen Proxy-Server (Port 3001)")
                proxy = MaxxiProxyServer(self.hass, listen_port=3001)

                async def _start_proxy():
                    try:
                        await proxy.start()
                        self.hass.data[DOMAIN]["proxy"] = proxy
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        _LOGGER.error("Fehler beim Starten des Proxy-Servers: %s", e)
                        self.hass.data[DOMAIN]["proxy"] = None

                task = self.hass.loop.create_task(_start_proxy())
                task.add_done_callback(
                    lambda t: _LOGGER.error("Proxy-Task beendet: %s", t.exception()) if t.exception() else None
                )

            else:
                proxy = self.hass.data[DOMAIN]["proxy"]
                _LOGGER.info("Proxy-Server läuft bereits – Gerät wird nur angebunden.")

            # Registriere diesen Entry beim Proxy
            try:
                proxy.register_entry(self.entry)
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error("Fehler beim Registrieren des Proxy-Eintrags: %s", e)

        else:
            _LOGGER.info("Lokaler Cloud-Proxy für dieses Gerät deaktiviert.")

        try:
            # Device-ID prüfen
            await self.check_device_id_issue()
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Prüfen der Device ID: %s", e)

        return True

    async def async_unload(self) -> None:
        raise NotImplementedError
   
    async def check_device_id_issue(self) -> None:
        """Prüfen, ob die Device ID gesetzt wurde."""
        _LOGGER.debug("CHECK Device_ID.....")
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            device_id = self.entry.data.get(CONF_DEVICE_ID)
            if not device_id:
                _LOGGER.error("Device-ID fehlt für Entry %s (%s)", entry.entry_id, entry.title)
                async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"missing_device_id_{entry.entry_id}",
                    is_fixable=False,
                    severity=IssueSeverity.CRITICAL,
                    issue_domain=DOMAIN,
                    translation_key="missing_device_id",
                    translation_placeholders={"entry_title": entry.title},
                )
            else:
                async_delete_issue(self.hass, DOMAIN, f"missing_device_id_{entry.entry_id}")
        _LOGGER.debug("Device_ID checked.")
