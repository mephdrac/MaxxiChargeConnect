"""
Initialisierung der MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul registriert beim Setup den Webhook und leitet den
Konfigurations-Flow an die zuständigen Plattformen weiter.
"""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .connection.ccu_base_connection import CcuBaseConnection
from .connection.ccu_v1_connection import ccuV1Connection
from .connection.ccu_v2_connection import ccuV2Connection

from .const import (
    CONF_CCU_VERSION,
    CCU_V1,
    CCU_V2,
    CONF_DEVICE_ID,
    CONF_NEEDS_DEVICE_ID,    
    DOMAIN    
)
from .webhook import async_unregister_webhook

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:  # pylint: disable=unused-argument
    """Wird beim Start von Home Assistant einmalig aufgerufen."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["proxy"] = None  # Platz für globale Proxy-Instanz
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup einer MaxxiChargeConnect Config Entry."""

    ccu_version = entry.data.get(CONF_CCU_VERSION, CCU_V1)
    connection: CcuBaseConnection | None = None
    
    _LOGGER.warning("CCU-Version: %s", ccu_version)

    if ccu_version == CCU_V1:
        connection = ccuV1Connection(hass, entry)

    elif ccu_version == CCU_V2:
        connection = ccuV2Connection(hass, entry)

    else:
        _LOGGER.error("Unbekannte CCU-Version: %s", ccu_version)
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["connection"] = connection

    return await connection.async_setup_entry()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlädt die Integration vollständig und deregistriert den Webhook."""
    await async_unregister_webhook(hass, entry)

    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in (PLATFORMS)]
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

    _LOGGER.info("MaxxiChargeConnect - config v%s.%s installiert", version, minor_version)
    # await check_device_id_issue(hass)
    return version == 3 and minor_version == 4
