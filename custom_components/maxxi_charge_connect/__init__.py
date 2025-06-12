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

from .const import DOMAIN
from .webhook import async_register_webhook, async_unregister_webhook

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):   # pylint: disable=unused-argument
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

    await async_register_webhook(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool: \
        # pylint: disable=unused-argument
    """Migrationsfunktion für künftige Änderungen an gespeicherten ConfigEntries.

    Derzeit wird keine Migration benötigt. Es wird lediglich ein Debug-Log ausgegeben.

    Args:
        hass: Die Home Assistant-Instanz.
        config_entry: Der zu migrierende Konfigurationseintrag.

    Returns:
        True: Migration (falls nötig) erfolgreich abgeschlossen.

    """

    _LOGGER.debug("Migration called for entry: %s", config_entry.entry_id)
    return True


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
