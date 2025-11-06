"""Sensor zur Anzeige der CCU-Temperatur."""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfTemperature, EntityCategory
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class CCUTemperaturSensor(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der CCU-Temperatur."""

    _attr_translation_key = "CCUTemperaturSensor"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für CCU-Temperatur.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ccu_temperatur_sensor"
        self._attr_icon = "mdi:temperature-celsius"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def handle_update(self, data):
        """Behandelt ccutemperaturn vom Maxxicharge."""

        if not data or "convertersInfo" not in data:
            _LOGGER.debug("Keine Daten für CCU-Temperatur vorhanden")
            self._attr_native_value = None
        else:
            ccu_temperaturen = [
                conv["ccuTemperature"] for conv in data["convertersInfo"]
            ]
            durchschnitt = sum(ccu_temperaturen) / len(ccu_temperaturen)
            self._attr_native_value = durchschnitt
            _LOGGER.debug("CCU-Temperatur aktualisiert: %s °C", self._attr_native_value)

        self.async_write_ha_state()
