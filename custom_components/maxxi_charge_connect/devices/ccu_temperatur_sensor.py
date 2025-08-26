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
from ..tools import is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class CCUTemperaturSensor(SensorEntity):
    """Sensor-Entität zur Anzeige der CCU-Temperatur."""

    _attr_translation_key = "CCUTemperaturSensor"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für CCU-Temperatur.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        self._entry = entry
        # self._attr_name = "PV Power"
        self._attr_unique_id = f"{entry.entry_id}_ccu_temperatur_sensor"
        self._attr_icon = "mdi:temperature-celsius"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Registriert den Sensor im Home Assistant Event-System.

        Verbindet sich mit dem Dispatcher, um auf Webhook-Updates zu reagieren.
        """

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")
            signal_sensor = (
                f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
            )

            self.async_on_remove(
                async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
            )

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

    async def _handle_update(self, data):
        """Behandelt ccutemperaturn vom Maxxicharge."""

        ccu_temperaturen = [conv["ccuTemperature"] for conv in data["convertersInfo"]]
        durchschnitt = sum(ccu_temperaturen) / len(ccu_temperaturen)

        self._attr_native_value = durchschnitt
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """

        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
