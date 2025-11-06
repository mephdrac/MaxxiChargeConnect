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

from .base_webhook_sensor import BaseWebhookSensor

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

    async def handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen Daten, erwartet ein 'SOC'-Feld mit dem Prozentwert.

        """
        self._attr_native_value = data.get("SOC", 0)
        self._attr_available = True
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
