"""Sensor zur Anzeige der aktuellen Photovoltaik-Leistung (PV Power).

Dieser Sensor visualisiert den aktuellen Gesamtwert der erzeugten Leistung
aus allen PV-Modulen, wie er vom MaxxiCharge-System bereitgestellt wird.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DEVICE_INFO, DOMAIN, PROXY_ERROR_EVENTNAME, CONF_ENABLE_CLOUD_DATA  # noqa: TID252
from ..tools import is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class PvPower(SensorEntity):
    """Sensor-Entität zur Anzeige der PV-Gesamtleistung (`PV_power_total`)."""

    _attr_translation_key = "PvPower"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für PV-Leistung.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        self._entry = entry
        # self._attr_name = "PV Power"
        self._attr_unique_id = f"{entry.entry_id}_pv_power"
        self._attr_icon = "mdi:solar-power"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Registriert den Sensor im Home Assistant Event-System.

        Verbindet sich mit dem Dispatcher, um auf Webhook-Updates zu reagieren.
        """

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_ERROR_EVENTNAME, self.async_update_from_event
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
        await self._handle_update(json_data)

    async def _handle_update(self, data):
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
