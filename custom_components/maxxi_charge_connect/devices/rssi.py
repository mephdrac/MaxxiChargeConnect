"""Sensor für die WLAN-Signalstärke.

Dieses Modul enthält die Klasse Rssi, die einen Sensor für die WLAN-Signalstärke (RSSI)
innerhalb der Home Assistant Integration bereitstellt.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class Rssi(BaseWebhookSensor):
    """SensorEntity zur Messung der WLAN-Signalstärke (RSSI).

    Attributes:
        _attr_entity_registry_enabled_default (bool): Gibt an, ob die Entität standardmäßig
          im Entity Registry aktiviert ist (hier False).
        _attr_translation_key (str): Übersetzungsschlüssel für den Namen.
        _attr_has_entity_name (bool): Gibt an, ob die Entität einen eigenen Namen hat.
        _unsub_dispatcher: Callback zum Abbestellen der Dispatcher-Signale.
        _entry (ConfigEntry): Die ConfigEntry der Integration.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den RSSI Sensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag der Integration.

        """
        super().__init__(entry)
        self._unsub_dispatcher = None
        self._attr_unique_id = f"{entry.entry_id}_rssi"
        self._attr_icon = "mdi:wifi"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def handle_update(self, data):
        """Wird aufgerufen, beim Empfang neuer Daten vom Dispatcher.

        Aktualisiert den aktuellen Wert des Sensors mit der neuen Signalstärke.

        Args:
            data (dict): Ein Dictionary, das die neuen Sensordaten enthält,
                         insbesondere der Schlüssel 'wifiStrength' mit dem Wert der Signalstärke.

        """

        self._attr_native_value = data.get("wifiStrength")
        self.async_write_ha_state()
