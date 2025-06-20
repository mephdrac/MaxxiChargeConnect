"""Initialisierung der MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul registriert beim Setup den Webhook und leitet den Konfigurations-Flow
an die zuständigen Plattformen (z. B. Sensor) weiter.

Funktionen:
- async_setup: Wird einmal beim Start von Home Assistant aufgerufen.
- async_setup_entry: Initialisiert eine neue Instanz bei Hinzufügen der Integration.
- async_unload_entry: Entfernt die Instanz und deregistriert den Webhook.
- async_migrate_entry: Platzhalter für zukünftige Migrationslogik.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN
from .http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator
from .migration.migration_from_yaml import MigrateFromYaml
from .webhook import async_register_webhook, async_unregister_webhook

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):  # pylint: disable=unused-argument
    """Wird beim Start von Home Assistant einmalig aufgerufen.

    Aktuell keine Initialisierung notwendig.

    Args:
        hass: Die Home Assistant-Instanz.
        config: Die Konfigurationsdaten (z.B. aus configuration.yaml).

    Returns:
        True: Setup erfolgreich.

    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Initialisiert eine neue Instanz der Integration beim Hinzufügen über die UI.

    Registriert den Webhook und lädt die Sensor-Plattform.

    Args:
        hass: Die Home Assistant-Instanz.
        entry: Die Konfigurationseintragsinstanz.

    Returns:
        True: Setup erfolgreich.

    """

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    sensor_list = []
    sensor_list.append(("PowerMeterIp", "Messgerät IP:"))
    sensor_list.append(("PowerMeterType", "Messgerät Typ:"))
    sensor_list.append(("MaximumPower", "Maximale Leistung:"))
    sensor_list.append(("OfflineOutputPower", "Offline-Ausgangsleistung:"))
    sensor_list.append(("NumberOfBatteries", "Batterien im System:"))
    sensor_list.append(("OutputOffset", "Ausgabe korrigieren:"))
    sensor_list.append(("CcuSpeed", "CCU-Geschwindigkeit:"))
    sensor_list.append(("Microinverter", "Mikro-Wechselrichter-Typ:"))
    sensor_list.append(("ResponseTolerance", "Reaktionstoleranz:"))
    sensor_list.append(("MinimumBatteryDischarge", "Minimale Entladung der Batterie:"))
    sensor_list.append(("MaximumBatteryCharge", "Maximale Akkuladung:"))
    sensor_list.append(("DC/DC-Algorithmus", "DC/DC-Algorithmus:"))
    sensor_list.append(("Cloudservice", "Cloudservice:"))
    sensor_list.append(("LocalServer", "Lokalen Server nutzen:"))
    sensor_list.append(("APIRoute", "API-Route:"))

    coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)
    hass.data[DOMAIN]["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    await async_register_webhook(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])

    # entity_registry = async_get_entity_registry(hass)
    # Das ist die ID des Geräts, das mit dem ConfigEntry verknüpft ist
    # device_id = entry.device_id

    # ConfigEntry.get(CONF_WEBHOOK_ID, "")
    _LOGGER.error("TITEL: %s", entry)

    # if device_id is not None:
    #     device = entity_registry.async_get(device_id)
    #     if device:
    #         device_name = device.name_by_user or device.name or "Unbekanntes Gerät"
    #         _LOGGER.error(f"Name des verknüpften Geräts: {device_name}")
    #     else:
    #         _LOGGER.warning("Kein Gerät zu device_id gefunden.")
    # else:
    #     _LOGGER.warning("Kein device_id im ConfigEntry vorhanden.")

    migrator = MigrateFromYaml(hass, entry)
    await migrator.async_notify_possible_migration()

    # Migrationsservice für die Yaml-Konfiguration von Joern-R registrieren

    async def handle_trigger_migration(call):
        mappings = call.data.get("mappings", [])
        await migrator.async_handle_trigger_migration(mappings)

    hass.services.async_register(
        DOMAIN, "migration_von_yaml_konfiguration", handle_trigger_migration
    )

    return True


# pylint: disable=too-many-statements
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migration eines Config-Eintrags von Version 1 auf Version 2.

    Args:
        hass (HomeAssistant): Home Assistant Instanz.
        config_entry (ConfigEntry): Zu migrierender Konfiguration^seintrag.

    Returns:
        bool: True, falls Migration durchgeführt wurde, sonst False.

    """
    version = config_entry.version
    minor_version = config_entry.minor_version

    _LOGGER.info("Prüfe Migration: Aktuelle Version: %s.%s", version, minor_version)

    if version < 2:
        _LOGGER.info("Migration MaxxiChargeConnect v1 → v2 gestartet")
        new_data = {**config_entry.data}
        version = 2
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=version
        )

    if version == 2:
        _LOGGER.info("Migration MaxxiChargeConnect v2 → v3 gestartet")

        # Entferne Sensor mit der alten unique_id
        entity_registry = async_get_entity_registry(hass)
        # Liste der veralteten unique_ids
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

        return True

    if version == 3 and minor_version == 0:
        _LOGGER.warning("Migration MaxxiChargeConnect v3.0 → v3.1 gestartet")

        try:
            # Entferne Sensor mit der alten unique_id
            entity_registry = async_get_entity_registry(hass)

            keys = []
            keys.append(("battery_energy_charge_today", "batterytodayenergycharge"))
            keys.append(
                ("battery_energy_discharge_today", "batterytodayenergydischarge")
            )
            keys.append(("battery_energy_total_charge", "batterytotalenergycharge"))
            keys.append(
                ("battery_energy_total_discharge", "batterytotalenergydischarge")
            )
            keys.append(("CcuEnergyToday", "ccuenergytoday"))
            keys.append(("ccu_energy_total", "ccuenergytotal"))
            keys.append(("grid_export_energy_today", "gridexportenergytoday"))
            keys.append(("grid_export_energy_total", "gridexportenergytotal"))
            keys.append(("grid_import_energy_today", "gridimportenergytoday"))
            keys.append(("grid_import_energy_total", "gridimportenergytotal"))
            keys.append(
                ("pv_self_consumption_energy_today", "pvselfconsumptionenergytoday")
            )
            keys.append(
                ("pv_self_consumption_energy_total", "pvselfconsumptionenergytotal")
            )
            keys.append(("pv_energy_today", "pvtodayenergy"))
            keys.append(("pv_energy_total", "pvtotalenergy"))

            for old_key, new_key in keys:
                old_unique_id = f"{config_entry.entry_id}_{old_key}"
                new_unique_id = f"{config_entry.entry_id}_{new_key}"

                _LOGGER.info("Suchen nach: %s", old_unique_id)

                # Suche die alte Entität im Entity Registry
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", "maxxi_charge_connect", old_unique_id
                )

                if entity_id:
                    _LOGGER.info("Ersetze mit: %s", new_unique_id)
                    entity_registry.async_update_entity(
                        entity_id, new_unique_id=new_unique_id
                    )

            version = 3
            minor_version = 1
            hass.config_entries.async_update_entry(
                config_entry, version=version, minor_version=minor_version
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Fehler beim migrieren: %s", e)
            return False

        return True

    _LOGGER.info("MaxxiChargeConnect - config v3.1 installiert")
    return version == 3 and minor_version == 1  # true == aktuelle Version


# async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
#     # pylint: disable=unused-argument
#     """Migrationsfunktion für künftige Änderungen an gespeicherten ConfigEntries.

#     Derzeit wird keine Migration benötigt. Es wird lediglich ein Debug-Log ausgegeben.

#     Args:
#         hass: Die Home Assistant-Instanz.
#         config_entry: Der zu migrierende Konfigurationseintrag.

#     Returns:
#         True: Migration (falls nötig) erfolgreich abgeschlossen.

#     """

#     _LOGGER.warning("Migration called for entry: %s", config_entry.entry_id)
#     return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Entlädt die Integration vollständig und deregistriert den Webhook.

    Args:
        hass: Die Home Assistant-Instanz.
        entry: Der zu entladende Konfigurationseintrag.

    Returns:
        True, wenn das Entladen erfolgreich war.

    """
    await async_unregister_webhook(hass, entry)

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
