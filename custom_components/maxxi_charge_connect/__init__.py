"""Initialisierung und Migration der MaxxiChargeConnect-Integration.

Das Modul initialisiert den Integrationsspeicher und richtet für jeden
Konfigurationseintrag die passende Verbindung zur CCU V1 oder CCU V2 ein.
Es entlädt die zugehörigen Plattformen und Verbindungen und migriert
vorhandene Konfigurationseinträge sowie ausgewählte Entitätskennungen.
Der Webhook wird durch die zuständige CCU-V1-Verbindung registriert.
"""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .connection.ccu_base_connection import CcuBaseConnection
from .connection.ccu_v1_connection import CCCv1Connection
from .connection.ccu_v2_connection import CCUv2Connection
from .connection.mqtt_discovery import PLATFORMS as MQTT_PLATFORMS
from .const import CCU_V1, CCU_V2, CONF_CCU_VERSION, CONF_DEVICE_ID, CONF_NEEDS_DEVICE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # pylint: disable=invalid-name

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


def _remove_legacy_webhook_entity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Entferne die veraltete Webhook-ID-Entität des Konfigurationseintrags.

    Die Bereinigung prüft die Zugehörigkeit zum aktuellen Config Entry,
    die Integrationsplattform und die bisherige Unique ID. Andere
    Entitäten und die intern gespeicherte Webhook-ID bleiben erhalten.

    Args:
        hass: Laufende Home-Assistant-Instanz mit Entity Registry.
        entry: Konfigurationseintrag der betreffenden CCU.

    Returns:
        None. Die Entity Registry wird bei einem Treffer direkt geändert.
    """
    registry = er.async_get(hass)
    old_unique_id = f"{entry.entry_id}_webhook_id"

    for entity_id, registry_entry in list(registry.entities.items()):
        if (
            registry_entry.config_entry_id == entry.entry_id
            and registry_entry.platform == DOMAIN
            and registry_entry.unique_id == old_unique_id
        ):
            registry.async_remove(entity_id)
            _LOGGER.info("Removed obsolete webhook ID entity: %s", entity_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:  # pylint: disable=unused-argument
    """Initialisiere den globalen Datenspeicher der Integration.

    Legt den Domain-Schlüssel an und initialisiert den Platzhalter für
    den optionalen Reverse-Proxy. Der eigentliche Geräteaufbau erfolgt
    erst in ``async_setup_entry``.

    Args:
        hass: Laufende Home-Assistant-Instanz.
        config: Vollständige Home-Assistant-Konfiguration; wird hier
            nicht ausgewertet, da die Einrichtung über Config Entries läuft.

    Returns:
        Immer ``True`` nach der Initialisierung.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["proxy"] = None  # Platz für globale Proxy-Instanz
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richte eine CCU-Verbindung für den angegebenen Config Entry ein.

    Entfernt zunächst die veraltete Webhook-ID-Entität, wählt anhand
    der konfigurierten CCU-Version die passende Verbindung und speichert
    diese unter der Entry-ID. Bei einem fehlgeschlagenen Setup wird
    die Verbindung entladen und aus dem Datenspeicher entfernt.

    Args:
        hass: Laufende Home-Assistant-Instanz.
        entry: Einzurichtender Konfigurationseintrag mit CCU-Version.

    Returns:
        ``True`` bei erfolgreichem Setup, andernfalls ``False``.
        Auch eine unbekannte CCU-Version führt zu ``False``.

    Raises:
        BaseException: Fehler aus dem Verbindungs-Setup werden nach dem
            Entfernen des zwischengespeicherten Eintrags weitergereicht.
    """

    _remove_legacy_webhook_entity(hass, entry)

    ccu_version = entry.data.get(CONF_CCU_VERSION, CCU_V1)
    connection: CcuBaseConnection | None = None

    _LOGGER.warning("CCU-Version: %s", ccu_version)

    if ccu_version == CCU_V1:
        connection = CCCv1Connection(hass, entry)

    elif ccu_version == CCU_V2:
        connection = CCUv2Connection(hass, entry)

    else:
        _LOGGER.error("Unbekannte CCU-Version: %s", ccu_version)
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["connection"] = connection

    try:
        setup_ok = await connection.async_setup_entry()
    except BaseException:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    if not setup_ok:
        await connection.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return setup_ok


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlade die Plattformen und die Verbindung eines Config Entries.

    Ermittelt die zu entladenden Plattformen abhängig von der CCU-Version.
    Erst wenn alle Plattformen erfolgreich entladen wurden, wird die
    Verbindung entladen und aus ``hass.data`` entfernt. Die zuständige
    Verbindung übernimmt dabei auch ihre Kommunikationsressourcen.

    Args:
        hass: Laufende Home-Assistant-Instanz.
        entry: Konfigurationseintrag, dessen Ressourcen freizugeben sind.

    Returns:
        ``True``, wenn sämtliche Plattformen erfolgreich entladen
        wurden; sonst ``False``. Bei ``False`` wird die Verbindung
        nicht aus dem Integrationsspeicher entfernt.
    """

    connection = hass.data[DOMAIN].get(entry.entry_id, {}).get("connection")
    platforms = [Platform(name) for name in MQTT_PLATFORMS] if entry.data.get(CONF_CCU_VERSION) == CCU_V2 else PLATFORMS

    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in platforms]
        )
    )

    if unload_ok:
        if connection is not None:
            await connection.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:  # pylint: disable=too-many-locals,too-many-branches, too-many-statements
    """Migriere einen vorhandenen Config Entry schrittweise auf Version 4.0.

    Führt nur die für die gespeicherte Version notwendigen Schritte aus:

    * v1 → v2: Übernahme der bestehenden Konfigurationsdaten.
    * v2 → v3: Entfernen ausgewählter veralteter Entitäten.
    * v3.0 → v3.1: Umbenennung der Unique IDs mehrerer Energiesensoren.
    * v3.1 → v3.2: Markierung einer fehlenden Device-ID zur Nacharbeit.
    * v3.2 → v3.3: Entfernen des alten Error-Sensors.
    * v3.3 → v3.4: Entfernen des alten Last-Message-Sensors.
    * v3.4 → v4.0: Ergänzung der CCU-Versionsangabe, falls sie fehlt.

    Die Migration verändert vorhandene Config Entries und gegebenenfalls
    zugehörige Entity-Registry-Einträge. Sie ist von der entfernten
    YAML-Konfigurationsmigration unabhängig.

    Args:
        hass: Laufende Home-Assistant-Instanz einschließlich Entity Registry.
        config_entry: Zu aktualisierender Konfigurationseintrag.

    Returns:
        ``True``, wenn am Ende Version 4.0 erreicht wurde; ``False``
        bei einem abgefangenen Migrationsfehler oder abweichender Version.
    """
    version = config_entry.version or 1
    minor_version = getattr(config_entry, "minor_version", 0)

    _LOGGER.info("Prüfe Migration: Aktuelle Version: %s.%s", version, minor_version)

    # --- Migrationen wie bisher ---
    if version < 2:
        try:
            _LOGGER.info("Migration MaxxiChargeConnect v1 → v2 gestartet")
            new_data = {**config_entry.data}
            version = 2
            hass.config_entries.async_update_entry(config_entry, data=new_data, version=version)
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
            if entity.config_entry_id == config_entry.entry_id and entity.unique_id in unique_ids_to_remove:
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
                entity_id = entity_registry.async_get_entity_id("sensor", "maxxi_charge_connect", old_unique_id)
                if entity_id:
                    entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)
            minor_version = 1
            hass.config_entries.async_update_entry(config_entry, version=version, minor_version=minor_version)
        except Exception as e:  # pylint: disable=broad-exception-caught
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
                if entry.config_entry_id == config_entry.entry_id and entry.unique_id == old_unique_id:
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
                if entry.config_entry_id == config_entry.entry_id and entry.unique_id == old_unique_id:
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

    if version == 3 and minor_version == 4:
        data = dict(config_entry.data)
        data.setdefault(CONF_CCU_VERSION, CCU_V1)
        version, minor_version = 4, 0
        hass.config_entries.async_update_entry(config_entry, data=data, version=version, minor_version=minor_version)

    _LOGGER.info("MaxxiChargeConnect - config v%s.%s installiert", version, minor_version)
    # await check_device_id_issue(hass)
    return version == 4 and minor_version == 0
