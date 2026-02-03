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

        pv_power_raw = data.get("PV_power_total")
        pr_raw = data.get("Pr")
        batteries = data.get("batteriesInfo", [])

        if not isinstance(batteries, list):
            _LOGGER.warning(
                "PvSelfConsumption: Invalid batteriesInfo type: %s", type(batteries)
            )
            batteries = []

        if pv_power_raw is None or pr_raw is None:
            _LOGGER.debug(
                "PvSelfConsumption: missing values (PV_power_total=%s, Pr=%s)",
                pv_power_raw,
                pr_raw,
            )
            return

        try:
            pv_power = float(pv_power_raw)
            pr = float(pr_raw)
        except (TypeError, ValueError) as err:
            _LOGGER.warning(
                "PvSelfConsumption: invalid values (PV_power_total=%s, Pr=%s): %s",
                pv_power_raw,
                pr_raw,
                err,
            )
            return

        if not is_power_total_ok(pv_power, batteries):
            return

        if not is_pr_ok(pr):
            return

        self._attr_native_value = round(pv_power - max(-pr, 0), 2)
