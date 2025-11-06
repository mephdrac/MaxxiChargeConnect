"""Sensor zur Berechnung des aktuellen Hausstromverbrauchs (PowerConsumption).

Dieser Sensor summiert die Leistung von Batterie (Pccu) und Netz (Pr), um den
aktuellen Gesamtstromverbrauch des Hauses zu bestimmen.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import is_pccu_ok, is_pr_ok  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class PowerConsumption(BaseWebhookSensor):
    """Sensor-Entität zur Erfassung des aktuellen Hausverbrauchs in Watt.

    Der Sensor summiert positive Batterie-Entladung (Pccu) und Netzimport (Pr),
    um den gesamten aktuellen Stromverbrauch zu berechnen.
    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "PowerConsumption"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Verbrauchssensor basierend auf Konfigurationsdaten.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_power_consumption"
        self._attr_icon = "mdi:home-import-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet eingehende Leistungsdaten und aktualisiert den Sensorwert.

        Die Verbrauchsberechnung lautet: Verbrauch = Pccu + max(-Pr, 0)

        Args:
            data (dict): Ein Dictionary mit Leistungswerten von Webhook-Daten.
                         Erwartet Schlüssel `Pccu` und `Pr`.

        """

        pccu = float(data.get("Pccu", 0))

        if is_pccu_ok(pccu):
            pr = float(data.get("Pr", 0))
            if is_pr_ok(pr):
                self._attr_native_value = round(pccu + max(pr, 0), 2)
                self.async_write_ha_state()
