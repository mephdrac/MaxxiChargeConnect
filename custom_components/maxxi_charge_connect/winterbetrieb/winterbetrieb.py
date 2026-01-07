# import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory


from ..const import (
    DEVICE_INFO,
    DOMAIN,
)
# _LOGGER = logging.getLogger(__name__)


class Winterbetrieb(SwitchEntity):
    """SwitchEntity für den Winterbetrieb."""

    _attr_translation_key = "Winterbetrieb"
    _attr_has_entity_name = True
    _attr_should_poll = False  # Switches sollten in der Regel nicht pollen

    def __init__(self, entry: ConfigEntry) -> None:

        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_winterbetrieb"

        self._state: bool = False
        # self._attr_icon = "mdi:identifier"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        # MUSS boolean zurückgeben, nicht None
        return bool(self._state)

    async def async_added_to_hass(self):
        """Wird aufgerufen, sobald die Entität registriert ist."""
        # Sicherstellen, dass der Switch initialen Wert korrekt anzeigt
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Schaltet den Winterbetrieb ein und aktiviert ggf. abhängige Sensoren."""
        self._state = True
        self.async_write_ha_state()
        # Optional: andere Sensoren aktivieren
        # await self._update_dependent_sensors()

    async def async_turn_off(self, **kwargs):
        """Schaltet den Winterbetrieb aus und deaktiviert ggf. abhängige Sensoren."""
        self._state = False
        self.async_write_ha_state()
        # Optional: andere Sensoren deaktivieren
        # await self._update_dependent_sensors()

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese  Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung
        """
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
