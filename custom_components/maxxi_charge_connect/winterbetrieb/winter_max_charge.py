"""NumberEntity für die maximale Ladung im Winterbetrieb."""

import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import callback

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    CONF_WINTER_MODE,
    WINTER_MODE_CHANGED_EVENT,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


# pylint: disable=abstract-method
class WinterMaxCharge(NumberEntity):
    """NumberEntity für die Anzeige der maximalen Ladung im Winterbetrieb."""

    _attr_translation_key = "winter_max_charge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_winter_max_charge"

        # self._attr_icon = "mdi:identifier"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = PERCENTAGE

        self._attr_native_max_value = 100
        self._attr_native_step = 1

        self.attr_native_min_value = entry.options.get(
            CONF_WINTER_MIN_CHARGE,
            DEFAULT_WINTER_MIN_CHARGE
        )

        self._attr_native_value = entry.options.get(
            CONF_WINTER_MAX_CHARGE,
            DEFAULT_WINTER_MAX_CHARGE
        )

        self._remove_listener = None

    def set_native_value(self, value):
        async def runner():
            await self.async_set_native_value(value)

        self.hass.create_task(runner())

    async def async_set_native_value(self, value: float) -> None:
        """Wird aufgerufen, wenn der User den Wert ändert."""

        self._attr_native_value = value

        # in hass.data spiegeln (für Logik / Availability)
        self.hass.data.setdefault(DOMAIN, {})

        self.hass.data[DOMAIN][CONF_WINTER_MAX_CHARGE] = value

        # persistent speichern
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_WINTER_MAX_CHARGE: value,
            },
        )

        # UI sofort aktualisieren
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        _LOGGER.debug("WinterMaxCharge available abgefragt: %s", not self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False))
        return self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)

    async def async_added_to_hass(self):
        """Registriert den Listener, wenn die Entität hinzugefügt wird."""
        self._remove_listener = self.hass.bus.async_listen(
            WINTER_MODE_CHANGED_EVENT,
            self._handle_winter_mode_changed,
        )

    async def async_will_remove_from_hass(self):
        """Entfernt den Listener, wenn die Entität entfernt wird."""
        if self._remove_listener:
            self._remove_listener()

    @callback
    def _handle_winter_mode_changed(self, event):  # pylint: disable=unused-argument
        """Handle winter mode changed event."""
        self.async_write_ha_state()

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
