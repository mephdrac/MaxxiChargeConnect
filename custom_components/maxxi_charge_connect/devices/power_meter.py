"""Sensor zur Darstellung der Momentanleistung am Netzanschlusspunkt (PowerMeter).

Dieser Sensor zeigt den aktuell gemessenen Wert von `Pr` an, also die
Import-/Exportleistung am Netzanschlusspunkt, wie sie vom MaxxiCharge-Gerät
geliefert wird.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import is_pr_ok  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class PowerMeter(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der Rohleistung (`Pr`) am Hausanschluss in Watt."""

    _attr_translation_key = "PowerMeter"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den PowerMeter-Sensor mit den Basisattributen.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz, die vom Benutzer gesetzt wurde.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_power_meter"
        self._attr_icon = "mdi:gauge"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Behandelt eingehende Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Dictionary mit dem Schlüssel `Pr`, der die momentane
                         Import-/Exportleistung repräsentiert. Wenn der Wert
                         fehlt oder ungültig ist, wird 0 als Default verwendet.

        """
        pr = data.get("Pr", 0)

        if is_pr_ok(pr):
            self._attr_native_value = pr
            self.async_write_ha_state()
