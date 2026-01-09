"""
Initialisierung der MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul registriert beim Setup den Webhook und leitet den
Konfigurations-Flow an die zuständigen Plattformen weiter.
"""

import asyncio
import logging

from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers import entity_registry as er

from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_NEEDS_DEVICE_ID,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    DOMAIN,
    NOTIFY_MIGRATION,
    OPTIONAL,
    REQUIRED,
    NEIN,
    DEFAULT_WINTER_MODE,
    CONF_WINTER_MODE,
    CONF_SUMMER_MIN_CHARGE,
    DEFAULT_SUMMER_MIN_CHARGE,
)
from .http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator
from .migration.migration_from_yaml import MigrateFromYaml
from .reverse_proxy.proxy_server import MaxxiProxyServer
from .webhook import async_register_webhook, async_unregister_webhook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def check_device_id_issue(hass):
    """Prüfen, ob die Device ID gesetzt wurde."""
    _LOGGER.debug("CHECK Device_ID.....")
    for entry in hass.config_entries.async_entries(DOMAIN):
        device_id = entry.data.get(CONF_DEVICE_ID)
        if not device_id:
            _LOGGER.error(
                "Device-ID fehlt für Entry %s (%s)", entry.entry_id, entry.title
            )
            async_create_issue(
                hass,
                DOMAIN,
                f"missing_device_id_{entry.entry_id}",
                is_fixable=False,
                severity=IssueSeverity.CRITICAL,
                issue_domain=DOMAIN,
                translation_key="missing_device_id",
                translation_placeholders={"entry_title": entry.title},
            )
        else:
            async_delete_issue(hass, DOMAIN, f"missing_device_id_{entry.entry_id}")
    _LOGGER.debug("Device_ID checked.")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:  # pylint: disable=unused-argument
    """Wird beim Start von Home Assistant einmalig aufgerufen."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["proxy"] = None  # Platz für globale Proxy-Instanz
    return True


# pylint: disable=too-many-locals, too-many-statements, too-many-branches
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialisiert eine neue Instanz der Integration beim Hinzufügen über die UI."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

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
    winter_mode = entry.options.get(
        CONF_WINTER_MODE,
        DEFAULT_WINTER_MODE,
    )

    summer_min_discharge = entry.options.get(
        CONF_SUMMER_MIN_CHARGE, DEFAULT_SUMMER_MIN_CHARGE
    )

    hass.data[DOMAIN][CONF_WINTER_MODE] = winter_mode
    hass.data[DOMAIN][CONF_SUMMER_MIN_CHARGE] = summer_min_discharge

    coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    # Webhook registrieren
    await async_register_webhook(hass, entry)

    try:
        # Plattformen laden
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error("Fehler beim Laden der Plattformen: %s", e)
        return False

    # Migration von YAML-Konfiguration
    migrator = MigrateFromYaml(hass, entry)

    async def handle_trigger_migration(call):
        mappings = call.data.get("mappings", [])

        try:
            if not isinstance(mappings, list) or not all(
                isinstance(item, dict) for item in mappings
            ):
                raise ValueError("Mappings must be a list of dictionaries.")
            for item in mappings:
                if "old_sensor" not in item or "new_sensor" not in item:
                    raise ValueError(
                        "Each mapping must contain 'old_sensor' and 'new_sensor'."
                    )
        except ValueError as e:
            _LOGGER.error("Invalid mappings provided for migration: %s", e)
            return

        try:
            await migrator.async_handle_trigger_migration(mappings)
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler bei der Migration: %s", e)

    hass.services.async_register(
        DOMAIN, "migration_von_yaml_konfiguration", handle_trigger_migration
    )

    # Migration-Hinweis
    notify_migration = entry.data.get(NOTIFY_MIGRATION, False)
    if notify_migration:

        async def sub_notify_migration():
            try:
                await asyncio.sleep(10)  # Warte 10 Sekunden nach Start
                await migrator.async_notify_possible_migration()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error("Fehler beim Migration-Hinweis: %s", e)

        task = hass.async_create_task(sub_notify_migration())
        task.add_done_callback(
            lambda t: _LOGGER.error("Notify-Migration-Task beendet: %s", t.exception())
            if t.exception()
            else None
        )

    # --- GLOBALEN PROXY starten ---
    proxy_enabled = entry.data.get(
        CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY
    )
    if proxy_enabled:
        if hass.data[DOMAIN]["proxy"] is None:
            _LOGGER.info("Starte globalen Proxy-Server (Port 3001)")
            proxy = MaxxiProxyServer(hass, listen_port=3001)

            async def _start_proxy():
                try:
                    await proxy.start()
                    hass.data[DOMAIN]["proxy"] = proxy
                except Exception as e:  # pylint: disable=broad-exception-caught
                    _LOGGER.error("Fehler beim Starten des Proxy-Servers: %s", e)
                    hass.data[DOMAIN]["proxy"] = None

            task = hass.loop.create_task(_start_proxy())
            task.add_done_callback(
                lambda t: _LOGGER.error("Proxy-Task beendet: %s", t.exception())
                if t.exception()
                else None
            )

        else:
            proxy = hass.data[DOMAIN]["proxy"]
            _LOGGER.info("Proxy-Server läuft bereits – Gerät wird nur angebunden.")

        # Registriere diesen Entry beim Proxy
        try:
            proxy.register_entry(entry)
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Registrieren des Proxy-Eintrags: %s", e)

    else:
        _LOGGER.info("Lokaler Cloud-Proxy für dieses Gerät deaktiviert.")

    try:
        # Device-ID prüfen
        await check_device_id_issue(hass)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error("Fehler beim Prüfen der Device ID: %s", e)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlädt die Integration vollständig und deregistriert den Webhook."""
    await async_unregister_webhook(hass, entry)

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in (PLATFORMS)
            ]
        )
    )

    # Proxy-Entry deregistrieren
    proxy = hass.data[DOMAIN].get("proxy")
    if proxy:
        try:
            proxy.unregister_entry(entry)
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Deregistrieren des Proxy-Eintrags: %s", e)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Prüfen, ob noch andere Einträge aktiv sind, bevor der Proxy gestoppt wird
    if proxy and not hass.config_entries.async_entries(DOMAIN):
        _LOGGER.info("Stoppe globalen Proxy-Server")

        try:
            await proxy.stop()
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Stoppen des Proxy-Servers: %s", e)
        finally:
            hass.data[DOMAIN]["proxy"] = None

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:  # pylint: disable=too-many-locals,too-many-branches, too-many-statements
    """Migration eines Config-Eintrags auf neuere Versionen."""
    version = config_entry.version or 1
    minor_version = getattr(config_entry, "minor_version", 0)

    _LOGGER.info("Prüfe Migration: Aktuelle Version: %s.%s", version, minor_version)

    # --- Migrationen wie bisher ---
    if version < 2:
        try:
            _LOGGER.info("Migration MaxxiChargeConnect v1 → v2 gestartet")
            new_data = {**config_entry.data}
            version = 2
            hass.config_entries.async_update_entry(
                config_entry, data=new_data, version=version
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    if version == 2:
        _LOGGER.info("Migration MaxxiChargeConnect v2 → v3 gestartet")
        entity_registry = async_get_entity_registry(hass)
        unique_ids_to_remove = [
            f"{config_entry.entry_id}_power_consumption",
            f"{config_entry.entry_id}_pv_self_consumption_energy_total",
            f"{config_entry.entry_id}_pv_self_consumption_energy_today",
        ]
        for entity in list(entity_registry.entities.values()):
            if (
                entity.config_entry_id == config_entry.entry_id
                and entity.unique_id in unique_ids_to_remove
            ):
                _LOGGER.info("Entferne veraltete Entität: %s", entity.entity_id)
                entity_registry.async_remove(entity.entity_id)
        version = 3
        hass.config_entries.async_update_entry(config_entry, version=version)

    if version == 3 and minor_version == 0:
        _LOGGER.info("Migration MaxxiChargeConnect v3.0 → v3.1 gestartet")
        try:
            # entity_registry = async_get_entity_registry(hass)

            entity_registry = er.async_get(hass)
            keys = [
                ("battery_energy_charge_today", "batterytodayenergycharge"),
                ("battery_energy_discharge_today", "batterytodayenergydischarge"),
                ("battery_energy_total_charge", "batterytotalenergycharge"),
                ("battery_energy_total_discharge", "batterytotalenergydischarge"),
                ("CcuEnergyToday", "ccuenergytoday"),
                ("ccu_energy_total", "ccuenergytotal"),
                ("grid_export_energy_today", "gridexportenergytoday"),
                ("grid_export_energy_total", "gridexportenergytotal"),
                ("grid_import_energy_today", "gridimportenergytoday"),
                ("grid_import_energy_total", "gridimportenergytotal"),
                ("pv_self_consumption_energy_today", "pvselfconsumptionenergytoday"),
                ("pv_self_consumption_energy_total", "pvselfconsumptionenergytotal"),
                ("pv_energy_today", "pvtodayenergy"),
                ("pv_energy_total", "pvtotalenergy"),
            ]
            for old_key, new_key in keys:
                old_unique_id = f"{config_entry.entry_id}_{old_key}"
                new_unique_id = f"{config_entry.entry_id}_{new_key}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", "maxxi_charge_connect", old_unique_id
                )
                if entity_id:
                    entity_registry.async_update_entity(
                        entity_id, new_unique_id=new_unique_id
                    )
            minor_version = 1
            hass.config_entries.async_update_entry(
                config_entry, version=version, minor_version=minor_version
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    if version == 3 and minor_version == 1:
        _LOGGER.warning("Migration MaxxiChargeConnect v3.1 → v3.2 gestartet")
        try:
            new_data = dict(config_entry.data)
            if CONF_DEVICE_ID not in new_data or not new_data[CONF_DEVICE_ID]:
                _LOGGER.warning(
                    "Device ID fehlt, setze leere Device ID und markiere zur Nachbearbeitung"
                )
                new_data[CONF_DEVICE_ID] = ""
                new_data[CONF_NEEDS_DEVICE_ID] = True
            minor_version = 2
            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                version=version,
                minor_version=minor_version,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    if version == 3 and minor_version == 2:
        _LOGGER.info("Migration MaxxiChargeConnect v3.2 → v3.3 gestartet")
        try:
            registry = er.async_get(hass)

            old_unique_id = f"{config_entry.entry_id}_error_sensor"

            for entity_id, entry in registry.entities.items():
                if entry.unique_id == old_unique_id:
                    registry.async_remove(entity_id)
                    _LOGGER.info(
                        "Alte Error-Sensor Entity entfernt:  %s | %s",
                        entity_id,
                        old_unique_id,
                    )
                    break

            minor_version = 3
            hass.config_entries.async_update_entry(
                config_entry,
                version=version,
                minor_version=minor_version,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    if version == 3 and minor_version == 3:
        _LOGGER.info("Migration MaxxiChargeConnect v3.3 → v3.4 gestartet")
        try:
            registry = er.async_get(hass)

            old_unique_id = f"{config_entry.entry_id}_last_message_sensor"

            for entity_id, entry in registry.entities.items():
                if entry.unique_id == old_unique_id:
                    registry.async_remove(entity_id)
                    _LOGGER.info(
                        "Alte Last-Message-Sensor Entity entfernt:  %s | %s",
                        entity_id,
                        old_unique_id,
                    )
                    break

            minor_version = 4
            hass.config_entries.async_update_entry(
                config_entry,
                version=version,
                minor_version=minor_version,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    _LOGGER.info(
        "MaxxiChargeConnect - config v%s.%s installiert", version, minor_version
    )
    await check_device_id_issue(hass)
    return version == 3 and minor_version == 4
