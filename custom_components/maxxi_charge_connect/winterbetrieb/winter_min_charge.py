"""NumberEntity für die minimale Entladeleistung im Winterbetrieb."""


import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import callback

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    CONF_WINTER_MODE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MAX_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
    WINTER_MODE_CHANGED_EVENT,
    EVENT_WINTER_MAX_CHARGE_CHANGED
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class WinterMinCharge(NumberEntity):
    """NumberEntity für die Anzeige der minimalen Entladeleistung im Winterbetrieb."""

    _attr_translation_key = "winter_min_charge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_winter_min_charge"

        # self._attr_icon = "mdi:identifier"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = PERCENTAGE
        self.attr_native_min_value = 0
        self._attr_native_step = 1

        self._attr_native_max_value = entry.options.get(
            CONF_WINTER_MAX_CHARGE,
            DEFAULT_WINTER_MAX_CHARGE
        )

        self._attr_native_value = entry.options.get(
            CONF_WINTER_MIN_CHARGE,
            DEFAULT_WINTER_MIN_CHARGE
        )
        self._remove_listener = None
        self._remove_listener_max_charge = None

    async def async_set_native_value(self, value: float) -> None:
        """Wird aufgerufen, wenn der User den Wert ändert."""

        self._attr_native_value = value

        # in hass.data spiegeln (für Logik / Availability)
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][CONF_WINTER_MIN_CHARGE] = value

        # persistent speichern
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_WINTER_MIN_CHARGE: value,
            },
        )
        # UI sofort aktualisieren
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        _LOGGER.debug("WinterMinCharge available abgefragt: %s", not self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False))
        return self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)

    async def async_added_to_hass(self):
        """Registriert den Listener, wenn die Entität hinzugefügt wird."""        
        # self.hass.data.setdefault(DOMAIN, {})
        # self.hass.data[DOMAIN][CONF_WINTER_MIN_CHARGE] = self._attr_native_value

        self._remove_listener = self.hass.bus.async_listen(
            WINTER_MODE_CHANGED_EVENT,
            self._handle_winter_mode_changed,
        )

        self._remove_listener_max_charge = self.hass.bus.async_listen(
            EVENT_WINTER_MAX_CHARGE_CHANGED,
            self._handle_winter_max_charge_changed,
        )

    async def async_will_remove_from_hass(self):
        """Entfernt den Listener, wenn die Entität entfernt wird."""
        if self._remove_listener:
            self._remove_listener()

    @callback
    def _handle_winter_mode_changed(self, event):  # Pylint: disable=unused-argument
        """Handle winter mode changed event."""
        self.async_write_ha_state()

    @callback
    async def _handle_winter_max_charge_changed(self, event):
        value = event.data.get("value")

        _LOGGER.debug("WinterMinCharge received max charge changed event: %s", value)

        if value is None:
            return

        try:
            value_float = float(value)
        except (ValueError, TypeError):
            _LOGGER.error("Konnte Wert nicht in float umwandeln: %s", value)
            return

        # Optional aktuellen Wert clampen
        if self._attr_native_value > value_float:
            await self.async_set_native_value(value_float)

        self._attr_native_max_value = value_float
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
