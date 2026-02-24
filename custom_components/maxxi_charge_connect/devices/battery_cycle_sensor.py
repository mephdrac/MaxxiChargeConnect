import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from ..tools import (
    get_entity
)


from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatteryCycleSensor(BaseWebhookSensor):

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatteryCycleSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        super().__init__(entry)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_cycle_sensor_{index}"
        #self._attr_icon = "mdi:battery-plus-variant"
        #self._attr_device_class = SensorDeviceClass.POWER
        #self._attr_state_class = SensorStateClass.MEASUREMENT
        #self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):

        batt_charge_unique_key = f"{self._entry.entry_id}_battery_charge_sensor_{self._index}"
        _LOGGER.debug("unique - from batterey_charge_sensor: key = %s", batt_charge_unique_key)

        entity = get_entity(self.hass, "maxxi_charge_connect", batt_charge_unique_key)
        _LOGGER.debug("BatteryCycleSensor: %s", entity.entity_id)
        
        return
        # """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.
        # Args:
        #     data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.
        # """
        # try:
        #     batteries_info = data.get("batteriesInfo", [])

        #     if not batteries_info or self._index >= len(batteries_info):
        #         _LOGGER.debug(
        #             "BatteryChargeSensor[%s]: Keine Batterie-Daten oder Index außerhalb Bereich",
        #             self._index
        #         )
        #         return

        #     battery_data = batteries_info[self._index]
        #     battery_power = battery_data.get("batteryPower")

        #     if battery_power is None:
        #         _LOGGER.debug(
        #             "BatteryChargeSensor[%s]: batteryPower fehlt",
        #             self._index
        #         )
        #         return

        #     # Konvertiere zu float
        #     charge_power = float(battery_power)

        #     # Nur positive Werte sind Ladeleistung
        #     if charge_power < 0:
        #         _LOGGER.debug(
        #             "BatteryChargeSensor[%s]: Negative Leistung (%s W) - keine Ladeleistung",
        #             self._index, charge_power
        #         )
        #         charge_power = 0

        #     # Plausibilitätsprüfung: Ladeleistung sollte vernünftig sein
        #     if charge_power > 20000:  # 20kW als vernünftige Obergrenze
        #         _LOGGER.warning(
        #             "BatteryChargeSensor[%s]: Unplausible Ladeleistung: %s W",
        #             self._index, charge_power
        #         )
        #         return

        #     self._attr_native_value = charge_power
        #     _LOGGER.debug(
        #         "BatteryChargeSensor[%s]: Aktualisiert auf %s W",
        #         self._index, charge_power
        #     )

        # except (IndexError, KeyError) as err:
        #     _LOGGER.warning(
        #         "BatteryChargeSensor[%s]: Datenstrukturfehler: %s",
        #         self._index, err
        #     )
        # except (ValueError, TypeError) as err:
        #     _LOGGER.warning(
        #         "BatteryChargeSensor[%s]: Konvertierungsfehler: %s",
        #         self._index, err
        #     )
