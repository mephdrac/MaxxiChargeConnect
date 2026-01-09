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
        CONF_WINTER_MIN_CHARGE,
        CONF_WINTER_MAX_CHARGE,
        WINTER_MODE_CHANGED_EVENT
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
        self._attr_unique_id = f"{entry.entry_id}_battery_soc"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._remove_listener = None

    async def async_added_to_hass(self):
        """Registriert den Listener, wenn die Entität hinzugefügt wird."""

        winter_betrieb = self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)
        _LOGGER.warning("BatterySoc async_added_to_hass: Winterbetrieb=%s", winter_betrieb)

        self._remove_listener = self.hass.bus.async_listen(
            WINTER_MODE_CHANGED_EVENT,
            self._handle_winter_mode_changed,
        )

    async def async_will_remove_from_hass(self):
        """Entfernt den Listener, wenn die Entität entfernt wird."""
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
        self._attr_native_value = data.get("SOC", 0)
        self._attr_available = True

        if self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False):
            # Im Wintermodus: UI sofort aktualisieren
            _LOGGER.warning("Wintermodus aktiv - spezielle Prüfung")
            winter_min_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MIN_CHARGE, 20))
            winter_max_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MAX_CHARGE, 60))

            _LOGGER.warning("SOC: %s, WinterMinCharge: %s, WinterMaxCharge: %s", self._attr_native_value, winter_min_charge, winter_max_charge)
            if self._attr_native_value <= winter_min_charge:
                _LOGGER.warning("Setze minSoc auf WinterMaxCarge: %s", winter_max_charge)
        else:
            # Im Normalmodus: UI sofort aktualisieren
            _LOGGER.warning("Normalmodus - UI wird aktualisiert")

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
