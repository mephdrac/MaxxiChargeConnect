"""Sensor zur Anzeige des aktuellen PV-Eigenverbrauchs.

Dieser Sensor zeigt die aktuell selbst genutzte Photovoltaik-Leistung an,
basierend auf der Differenz zwischen erzeugter PV-Leistung und Rückeinspeisung.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import is_power_total_ok, is_pr_ok  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class PvSelfConsumption(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige des PV-Eigenverbrauchs (PV Self-Consumption)."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "PvSelfConsumption"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den PV-Eigenverbrauchs-Sensor.

        Args:
            entry (ConfigEntry): Die Konfiguration der Integration.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_pv_consumption"
        self._attr_icon = "mdi:solar-power-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet neue Leistungsdaten zur Berechnung des PV-Eigenverbrauchs.

        Die Berechnung erfolgt nach der Formel:
        `PV_power_total - max(-Pr, 0)`, wobei Pr der Rückspeisewert ist.

        Args:
            data (dict): Die vom Webhook gesendeten Sensordaten.

        """

        pv_power = float(data.get("PV_power_total", 0))
        batteries = data.get("batteriesInfo", [])

        if is_power_total_ok(pv_power, batteries):
            pr = float(data.get("Pr", 0))

            if is_pr_ok(pr):
                self._attr_native_value = pv_power - max(-pr, 0)
                self.async_write_ha_state()
