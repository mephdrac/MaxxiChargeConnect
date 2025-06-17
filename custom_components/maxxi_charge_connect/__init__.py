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
from homeassistant.helpers import entity_registry as er
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN
from .webhook import async_register_webhook, async_unregister_webhook

from .http_scan.maxxi_data_update_coordinator import MaxxiDataUpdateCoordinator

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

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migration eines Config-Eintrags von Version 1 auf Version 2.

    Args:
        hass (HomeAssistant): Home Assistant Instanz.
        config_entry (ConfigEntry): Zu migrierender Konfiguration^seintrag.

    Returns:
        bool: True, falls Migration durchgeführt wurde, sonst False.

    """
    _LOGGER.info("Starte Migration: Aktuelle Version: %s", config_entry.version)

    version = config_entry.version

    if version < 2:
        _LOGGER.info("Migration MaxxiChargeConnect v1 → v2 gestartet")
        new_data = {**config_entry.data}
        # config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)
        version = 2

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

        # Version anpassen und übernehmen
        # Setze neue Version explizit
        version = 3
        hass.config_entries.async_update_entry(config_entry, version=3)
        # await hass.async_block_till_done()
        _LOGGER.info("Migration auf Version 3 abgeschlossen")

        return True

    if version == 3:
        _LOGGER.warning("Migration MaxxiChargeConnect v3 → v4 gestartet")
        # Entferne Sensor mit der alten unique_id
        entity_registry = async_get_entity_registry(hass)
        # registry = er.async_get(hass)

        old_unique_id = f"{config_entry.entry_id}_battery_energy_discharge_today"
        new_unique_id = f"{config_entry.entry_id}_batterytodayenergydischarge"

        _LOGGER.warning("Suchen nach: %s", old_unique_id)
        _LOGGER.warning("Ersetze mit: %s", new_unique_id)

        # Suche die alte Entität im Entity Registry
        entity_id = entity_registry.async_get_entity_id(
            "sensor", "maxxi_charge_connect", old_unique_id
        )

        if entity_id:
            entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)

        version = 4
        hass.config_entries.async_update_entry(config_entry, version=4)
        return True

    if version >= 4:
        return True

    return False


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
