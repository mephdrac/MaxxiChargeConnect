"""Sensor zur Anzeige der aktuellen Photovoltaik-Leistung (PV Power).

Dieser Sensor visualisiert den aktuellen Gesamtwert der erzeugten Leistung
aus allen PV-Modulen, wie er vom MaxxiCharge-System bereitgestellt wird.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import is_power_total_ok  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class PvPower(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der PV-Gesamtleistung (`PV_power_total`)."""

    _attr_translation_key = "PvPower"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für PV-Leistung.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_pv_power"
        self._attr_icon = "mdi:solar-power"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data: dict):
        """Behandelt eingehende Leistungsdaten von der MaxxiCharge-Station.

        Args:
            data (dict): Webhook-Daten, typischerweise mit `PV_power_total`
                         und `batteriesInfo`.

        """
        pv_power = float(data.get("PV_power_total", 0))
        batteries = data.get("batteriesInfo", [])

        if is_power_total_ok(pv_power, batteries):
            self._attr_native_value = pv_power
            self.async_write_ha_state()
