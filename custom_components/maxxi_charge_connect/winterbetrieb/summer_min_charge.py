"""NumberEntity für die minimale Entladeleistung im Winterbetrieb."""


import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE

# from homeassistant.core import callback

from ..const import (
        DEVICE_INFO,
        DOMAIN,
        CONF_WINTER_MODE,
        CONF_SUMMER_MIN_CHARGE,
        DEFAULT_SUMMER_MIN_CHARGE
    )

_LOGGER = logging.getLogger(__name__)


class SummerMinCharge(NumberEntity):
    """NumberEntity für die Anzeige der minimales Ladung im Sommerbetrieb."""

    _attr_translation_key = "summer_min_charge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_summer_min_charge"
        self._attr_icon = "mdi:battery-lock"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = PERCENTAGE
        self.attr_native_min_value = 0
        self._attr_native_step = 1
        self._attr_native_max_value = 100

        self._attr_native_value = entry.options.get(
            CONF_SUMMER_MIN_CHARGE,
            DEFAULT_SUMMER_MIN_CHARGE
        )
        self._remove_listener = None
        self._remove_listener_max_charge = None

    async def async_set_native_value(self, value: float) -> None:
        """Wird aufgerufen, wenn der User den Wert ändert."""

        self._attr_native_value = value

        # in hass.data spiegeln (für Logik / Availability)
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][CONF_SUMMER_MIN_CHARGE] = value

        # persistent speichern
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_SUMMER_MIN_CHARGE: value,
            },
        )
        # UI sofort aktualisieren
        self.async_write_ha_state()

    # @property
    # def available(self) -> bool:
    #     _LOGGER.debug("WinterMinCharge available abgefragt: %s", not self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False))
    #     return self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)

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
