"""Initialisierung der MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul registriert beim Setup den Webhook und leitet den
Konfigurations-Flow an die zuständigen Plattformen weiter.

Funktionen:
- async_setup: Wird einmal beim Start von Home Assistant aufgerufen.
- async_setup_entry: Initialisiert eine neue Instanz beim Hinzufügen.
- async_unload_entry: Entfernt die Instanz und deregistriert den Webhook.
- async_migrate_entry: Migrationslogik für ConfigEntries.
"""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.issue_registry import async_create_issue, async_delete_issue
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from .const import (
    DOMAIN,
    NOTIFY_MIGRATION,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_DEVICE_ID,
    CONF_NEEDS_DEVICE_ID,
)

from .http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator
from .migration.migration_from_yaml import MigrateFromYaml
from .webhook import async_register_webhook, async_unregister_webhook
from .reverse_proxy.proxy_server import MaxxiProxyServer

_LOGGER = logging.getLogger(__name__)
PROXY_INSTANCE = None  # globale Proxy-Instanz für Zugriff


async def check_device_id_issue(hass):

    _LOGGER.warning("CHECK.....")
    for entry in hass.config_entries.async_entries(DOMAIN):
        device_id = entry.data.get(CONF_DEVICE_ID)
        if not device_id:
            # Issue anlegen, wenn device_id fehlt
            async_create_issue(
                hass,
                DOMAIN,
                f"missing_device_id_{entry.entry_id}",
                is_fixable=True,
                severity="critical",
                translation_key="missing_device_id",
                translation_placeholders={"entry_title": entry.title},
            )
        else:
            # Issue löschen, wenn device_id da ist
            async_delete_issue(hass, DOMAIN, f"missing_device_id_{entry.entry_id}")

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Wird beim Start von Home Assistant einmalig aufgerufen.

    Aktuell keine Initialisierung notwendig.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialisiert eine neue Instanz der Integration beim Hinzufügen über die UI.

    Registriert den Webhook und lädt die Sensor- und Number-Plattformen.
    Zeigt Repair-Issue, wenn device_id fehlt.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    sensor_list = [
        ("PowerMeterIp", "Messgerät IP:"),
        ("PowerMeterType", "Messgerät Typ:"),
        ("MaximumPower", "Maximale Leistung:"),
        ("OfflineOutputPower", "Offline-Ausgangsleistung:"),
        ("NumberOfBatteries", "Batterien im System:"),
        ("OutputOffset", "Ausgabe korrigieren:"),
        ("CcuSpeed", "CCU-Geschwindigkeit:"),
        ("Microinverter", "Mikro-Wechselrichter-Typ:"),
        ("ResponseTolerance", "Reaktionstoleranz:"),
        ("MinimumBatteryDischarge", "Minimale Entladung der Batterie:"),
        ("MaximumBatteryCharge", "Maximale Akkuladung:"),
        ("DC/DC-Algorithmus", "DC/DC-Algorithmus:"),
        ("Cloudservice", "Cloudservice:"),
        ("LocalServer", "Lokalen Server nutzen:"),
        ("APIRoute", "API-Route:"),
    ]

    coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)
    hass.data[DOMAIN]["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    # Webhook registrieren
    await async_register_webhook(hass, entry)

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])

    # Migration von YAML-Konfiguration (optional)
    migrator = MigrateFromYaml(hass, entry)

    async def handle_trigger_migration(call):
        mappings = call.data.get("mappings", [])
        await migrator.async_handle_trigger_migration(mappings)

    hass.services.async_register(DOMAIN, "migration_von_yaml_konfiguration", handle_trigger_migration)

    # Automatische Benachrichtigung zur Migration, falls konfiguriert
    notify_migration = entry.data.get(NOTIFY_MIGRATION, False)
    if notify_migration:
        hass.async_create_task(migrator.async_notify_possible_migration())
   

    # Proxy-Server starten, falls aktiviert
    if entry.data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY):
        _LOGGER.info("Starte Proxy-Server")
        forward_to_cloud = entry.data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)

        proxy = MaxxiProxyServer(hass, listen_port=3001, enable_forward=forward_to_cloud)
        hass.loop.create_task(proxy.start())

        hass.data[DOMAIN]["proxy"] = proxy
        global PROXY_INSTANCE
        PROXY_INSTANCE = proxy

        async def periodic_check(now):
            await check_device_id_issue(hass)

        await check_device_id_issue(hass)
        async_track_time_interval(hass, periodic_check, timedelta(minutes=10))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlädt die Integration vollständig und deregistriert den Webhook."""

    await async_unregister_webhook(hass, entry)

    proxy = hass.data[DOMAIN].get("proxy")
    if proxy:
        await proxy.stop()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in ("sensor", "number")
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migration eines Config-Eintrags auf neuere Versionen.

    Führt alle erforderlichen Schritte aus, um alte Versionen zu aktualisieren.
    """
    version = config_entry.version or 1
    minor_version = getattr(config_entry, "minor_version", 0)

    _LOGGER.warning("Prüfe Migration: Aktuelle Version: %s.%s", version, minor_version)

    if version < 2:
        _LOGGER.warning("Migration MaxxiChargeConnect v1 → v2 gestartet")
        new_data = {**config_entry.data}
        version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=version)

    if version == 2:
        _LOGGER.warning("Migration MaxxiChargeConnect v2 → v3 gestartet")
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
        _LOGGER.info("Migration auf Version 3 abgeschlossen")

    if version == 3 and minor_version == 0:
        _LOGGER.warning("Migration MaxxiChargeConnect v3.0 → v3.1 gestartet")

        try:
            entity_registry = async_get_entity_registry(hass)
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

                _LOGGER.info("Suchen nach: %s", old_unique_id)

                entity_id = entity_registry.async_get_entity_id(
                    "sensor", "maxxi_charge_connect", old_unique_id
                )

                if entity_id:
                    _LOGGER.info("Ersetze mit: %s", new_unique_id)
                    entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)

            version = 3
            minor_version = 1
            hass.config_entries.async_update_entry(
                config_entry, version=version, minor_version=minor_version
            )
        except Exception as e:
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    if version == 3 and minor_version == 1:
        _LOGGER.warning("Migration MaxxiChargeConnect v3.1 → v3.2 gestartet")

        try:
            new_data = dict(config_entry.data)

            if CONF_DEVICE_ID not in new_data or not new_data[CONF_DEVICE_ID]:
                _LOGGER.warning("Device ID fehlt, setze leere Device ID und markiere zur Nachbearbeitung")
                new_data[CONF_DEVICE_ID] = ""
                new_data[CONF_NEEDS_DEVICE_ID] = True

            version = 3
            minor_version = 2
            hass.config_entries.async_update_entry(
                config_entry, data=new_data, version=version, minor_version=minor_version
            )
        except Exception as e:
            _LOGGER.error("Fehler beim Migrieren der Konfiguration: %s", e)
            return False

    _LOGGER.warning("MaxxiChargeConnect - config v%s.%s installiert", version, minor_version)
    await check_device_id_issue(hass)
    return version == 3 and minor_version == 2
