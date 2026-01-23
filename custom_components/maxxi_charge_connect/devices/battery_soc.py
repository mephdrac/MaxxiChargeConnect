"""Battery SOC Sensor für MaxxiChargeConnect.

Dieses Modul definiert die BatterySoc-Sensor-Entity, die den Ladezustand (State of Charge, SOC)
der Batterie in Prozent darstellt. Der Sensor empfängt die Werte über einen Dispatcher,
der durch Webhook-Daten aktualisiert wird.

Der Sensor wird dynamisch in Home Assistant registriert und aktualisiert.
"""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback

from .base_webhook_sensor import BaseWebhookSensor

from ..const import (
        DOMAIN,
        CONF_WINTER_MODE,
        WINTER_MODE_CHANGED_EVENT,
        CONF_WINTER_MIN_CHARGE,
        CONF_WINTER_MAX_CHARGE,
    )

from ..tools import (
    get_entity
)


_LOGGER = logging.getLogger(__name__)


class BatterySoc(BaseWebhookSensor):
    """SensorEntity zur Darstellung des Ladezustands (SOC) einer Batterie in Prozent.

    Der Sensor verwendet Dispatcher-Signale, um sich automatisch zu aktualisieren,
    sobald neue Daten über den konfigurierten Webhook empfangen werden.
    """

    _attr_translation_key = "BatterySoc"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den BatterySoc-Sensor.

        Args:
            entry (ConfigEntry): Die Konfigurationsdaten aus dem Home Assistant ConfigEntry.

        """
        super().__init__(entry)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_battery_soc"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._remove_listener = None

    async def async_added_to_hass(self):
        """Registriert den Listener, wenn die Entität hinzugefügt wird."""
        await super().async_added_to_hass()

        winter_betrieb = self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)
        _LOGGER.warning("BatterySoc async_added_to_hass: Winterbetrieb=%s", winter_betrieb)

        self._remove_listener = self.hass.bus.async_listen(
            WINTER_MODE_CHANGED_EVENT,
            self._handle_winter_mode_changed,
        )

    async def async_will_remove_from_hass(self):
        """Entfernt den Listener, wenn die Entität entfernt wird."""
        await super().async_will_remove_from_hass()

        if self._remove_listener:
            self._remove_listener()

    @callback
    def _handle_winter_mode_changed(self, event):  # Pylint: disable=unused-argument
        """Handle winter mode changed event."""

        winter_mode_enabled = event.data.get("enabled")
        _LOGGER.warning("WinterMinCharge received winter mode changed event: %s", winter_mode_enabled)

        if winter_mode_enabled is None:
            winter_mode_enabled = event.data.get("enabled", False)

        _LOGGER.warning("WinterMinCharge received winter mode changed event: %s", winter_mode_enabled)
        self.async_write_ha_state()

    async def handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen Daten, erwartet ein 'SOC'-Feld mit dem Prozentwert.

        """
        try:
            native_value_float = float(str(data.get("SOC")).strip())
            self._attr_available = True
        except (ValueError, TypeError):
            _LOGGER.error(
                "Ungültiger SOC-Wert empfangen: %r", self._attr_native_value
            )
            self._attr_available = False
            return

        self._attr_native_value = native_value_float
        wintermode = self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)
        _LOGGER.debug("BatterySoc received webhook update: SOC=%s, Wintermode=%s, updating state.", self._attr_native_value, wintermode)

        if wintermode:
            # Im Wintermodus: UI sofort aktualisieren
            _LOGGER.debug("Wintermodus aktiv - spezielle Prüfung")
            winter_min_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MIN_CHARGE, 20))
            winter_max_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MAX_CHARGE, 60))

            if self._attr_native_value is not None:

                _LOGGER.debug("Prüfe ob minSoc angepasst werden muss: native_value=%s, winter_min_charge=%s", native_value_float, winter_min_charge)

                # Hole minSoc Entity
                coordinator = self.hass.data[DOMAIN][self._entry.entry_id]["coordinator"]
                rest_key = "minSOC"
                unique_id = f"{coordinator.entry.entry_id}_{rest_key}"

                min_soc_entity = get_entity(
                        hass=self.hass,
                        plattform=DOMAIN,
                        unique_id=unique_id
                    )

                if min_soc_entity is None:
                    _LOGGER.error("min_soc_entity nicht gefunden für unique_id: %s", unique_id)
                    return

                cur_state = self.hass.states.get(min_soc_entity.entity_id)
                _LOGGER.warning("Current state of min_soc entity %s: %s", min_soc_entity.entity_id, cur_state.state if cur_state else "State not found")

                if (cur_state is not None and cur_state.state not in ("unknown", "unavailable")):  # Nur wenn der Zustand bekannt ist
                    cur_state_float = float(cur_state.state)

                    if native_value_float <= winter_min_charge and cur_state_float != winter_max_charge:
                        _LOGGER.warning("Setze minSoc auf WinterMaxCarge: %s", winter_max_charge)

                        await self.hass.services.async_call(
                            "number",
                            "set_value",
                            {
                                "entity_id": min_soc_entity.entity_id,
                                "value": winter_max_charge,
                            },
                            blocking=True,
                        )
                    elif native_value_float >= winter_max_charge and cur_state_float != winter_min_charge:
                        _LOGGER.warning("Setze minSoc auf WinterMinCharge: %s", winter_min_charge)

                        await self.hass.services.async_call(
                            "number",
                            "set_value",
                            {
                                "entity_id": min_soc_entity.entity_id,
                                "value": winter_min_charge,
                            },
                            blocking=True,
                        )
                    else:
                        _LOGGER.debug("Keine Anpassung des min_soc erforderlich.")
                else:
                    _LOGGER.warning("Current state of min_soc entity is None.")
            else:
                _LOGGER.debug("Native value ist None im Wintermodus.")
        else:
            # Im Normalmodus: UI sofort aktualisieren
            _LOGGER.debug("Normalmodus - UI wird aktualisiert")

        self.async_write_ha_state()

    @property
    def icon(self):
        """Return dynamic battery icon based on SOC percentage."""
        result = "mdi:battery-unknown"

        try:
            level = max(0, min(100, int(self._attr_native_value)))  # Clamping 0–100
            level = round(level / 10) * 10  # z. B. 57 → 60

            # _LOGGER.warning("Level: %s", level)

        except (TypeError, ValueError):
            result = "mdi:battery-unknown"
        else:
            if level == 100:
                result = "mdi:battery"
            elif level == 0:
                result = "mdi:battery-outline"
            else:
                result = f"mdi:battery-{level}"
        return result
