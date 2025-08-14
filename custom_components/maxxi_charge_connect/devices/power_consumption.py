"""Sensor zur Berechnung des aktuellen Hausstromverbrauchs (PowerConsumption).

Dieser Sensor summiert die Leistung von Batterie (Pccu) und Netz (Pr), um den
aktuellen Gesamtstromverbrauch des Hauses zu bestimmen.
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
from ..tools import is_pccu_ok, is_pr_ok  # noqa: TID252


_LOGGER = logging.getLogger(__name__)


class PowerConsumption(SensorEntity):
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
        self._entry = entry
        self._attr_suggested_display_precision = 2
        # self._attr_name = "House Consumption"
        self._attr_unique_id = f"{entry.entry_id}_power_consumption"
        self._attr_icon = "mdi:home-import-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird.

        Verbindet sich mit dem Dispatcher-Signal zur Aktualisierung des Sensors,
        basierend auf den eingehenden Webhook-Daten.
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
