"""
Text-Entity-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert die Klasse `HttpScanText`, die diagnostische Text-Entitäten
bereitstellt, um aus HTML extrahierte Werte anzuzeigen. Die Werte stammen von einem
Koordinator, der die Daten regelmäßig aktualisiert.
"""

import logging
from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from ..const import DEVICE_INFO, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HttpScanText(TextEntity):
    """Text-Entität zur Anzeige diagnostischer Daten aus einem HTML-Scanner."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, keyname, name, icon) -> None:  # pylint: disable=unused-argument
        """Initialisiert eine neue HttpScanText-Entität.

        Args:
            coordinator: Der DataUpdateCoordinator, der die HTML-Daten liefert.
            keyname (str): Der Schlüssel für die extrahierten Daten, z.B. "PowerMeterIp".
            name (str): Anzeigename der Entität\
                (nicht verwendet, falls `_attr_has_entity_name = True`).
            icon (str): Icon der Entität (Material Design Icon-Name, z.B. "mdi:network").

        """

        self._attr_translation_key = keyname
        self.coordinator = coordinator
        self._keyname = keyname
        # self._attr_name = name
        self._entry = coordinator.entry
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{keyname}"

        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_should_poll = False

    @property
    def native_value(self):
        """Gibt den aktuellen Wert der Text-Entität zurück.

        Returns:
            str | None: Der extrahierte Wert aus dem Koordinator oder None,
                        falls keine Daten vorhanden sind.

        """
        return (
            self.coordinator.data.get(self._keyname) if self.coordinator.data else None
        )

    async def async_added_to_hass(self):
        """Registriert Callback bei Datenaktualisierung durch den Koordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    def set_value(self, value):
        """SetValue."""
        self._attr_native_value = value

    @property
    def device_info(self) -> DeviceInfo:
        """Gibt die Geräteinformationen für diese Entität zurück.

        Returns:
            DeviceInfo: Informationen zur Verknüpfung mit dem physischen Gerät,
                        z.B. Name, Hersteller, Modell.

        """
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
