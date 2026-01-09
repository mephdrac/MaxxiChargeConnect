"""SwitchEntity für den Winterbetrieb in der MaxxiCharge Connect Integration."""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    CONF_WINTER_MODE,
    WINTER_MODE_CHANGED_EVENT
)

from ..tools import get_number_entity_id

_LOGGER = logging.getLogger(__name__)


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

    async def async_added_to_hass(self):
        """Wird aufgerufen, sobald die Entität registriert ist."""
        # Sicherstellen, dass der Switch initialen Wert korrekt anzeigt
        self._state = self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Gibt den aktuellen Zustand des Winterbetriebs zurück."""
        # MUSS boolean zurückgeben, nicht None
        return bool(self._state)

    def turn_on(self, **kwargs):
        """Schaltet den Winterbetrieb ein."""
        return self.async_turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Schaltet den Winterbetrieb aus."""
        return self.async_turn_off(**kwargs)

    async def async_turn_on(self, **kwargs):
        """Schaltet den Winterbetrieb ein und aktiviert ggf. abhängige Sensoren."""
        _LOGGER.debug("Winterbetrieb aktiviert")
        await self.async_enable_winter_mode()

    async def async_turn_off(self, **kwargs):
        """Schaltet den Winterbetrieb aus und deaktiviert ggf. abhängige Sensoren."""
        _LOGGER.debug("Winterbetrieb deaktiviert")
        await self._save_state(False)

    async def _save_state(self, value: bool):
        """Speichert den aktuellen Zustand des Winterbetriebs in den Eintragsoptionen."""
        self._state = value
        self.hass.data[DOMAIN][CONF_WINTER_MODE] = value

        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_WINTER_MODE: value,
            },
        )
        self._notify_dependents()
        self.async_write_ha_state()

    def _notify_dependents(self):
        """Benachrichtigt abhängige Entitäten über den Wechsel des Winterbetriebs."""
        self.hass.bus.async_fire(
            WINTER_MODE_CHANGED_EVENT,
            {"enabled": self._state},
        )

    async def async_enable_winter_mode(self):
        # aktuellen Wert holen

        state = self.hass.states.get("sensor.maxxitest_minimale_entladung_der_batterie")

        _LOGGER.warning("Aktueller Zustand der Entität: %s", state)

        # if state is None:
        #     _LOGGER.warning("Entity nicht gefunden")
        #     return

        # current_value = float(state.state)

        # # im ConfigEntry merken
        # data = dict(self._entry.data)
        # data["value_before_winter"] = current_value

        # self.hass.config_entries.async_update_entry(
        #     self._entry,
        #     data=data,
        # )

        await self._save_state(True)

        # _LOGGER.debug(
        #     "Winterbetrieb aktiviert – Wert gemerkt: %s",
        #     current_value,
        # )

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
