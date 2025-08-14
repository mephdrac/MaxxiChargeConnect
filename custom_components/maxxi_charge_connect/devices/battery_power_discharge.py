"""Sensorentität zur Darstellung der Batterieentladeleistung für MaxxiCharge.

Dieses Modul definiert die `BatteryPowerDischarge`-Entität, die in Home Assistant
eingebunden wird, um den Entladestrom der Batterie basierend auf Daten aus einem
Webhook zu visualisieren. Sie aktualisiert sich automatisch bei eingehendem Signal
und nutzt standardisierte Sensor-Attribute wie Leistungseinheit, Geräteklasse und
Zustandsklasse.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import Event

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_ERROR_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryPowerDischarge(SensorEntity):
    """Sensorentität zur Anzeige der aktuellen Batterieentladeleistung (Watt).

    Diese Entität berechnet die Entladeleistung der Batterie basierend auf der
    Differenz zwischen Photovoltaik-Leistung (PV_power_total) und dem Stromverbrauch
    (Pccu). Wenn die Differenz negativ ist, wird die absolute Differenz als
    Entladeleistung interpretiert – ansonsten wird 0 angezeigt.

    Die Entität registriert sich bei einem Dispatcher-Signal, das über einen
    Webhook mit aktuellen Leistungsdaten versorgt wird, und aktualisiert sich
    entsprechend.

    Die Entität wird standardmäßig im Entity-Registry aktiviert und nutzt
    standardisierte Geräteeigenschaften für Darstellung und Klassifikation.
    """

    _attr_translation_key = "BatteryPowerDischarge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Sensor-Entität.

        Args:
            entry (ConfigEntry): Die Konfigurationsdaten dieser Instanz.

        Setzt die Geräteattribute wie Icon, Einheit, Gerätetyp und eindeutige ID.

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        #    self._attr_name = "Battery Power Discharge"
        self._attr_unique_id = f"{entry.entry_id}_battery_power_discharge"
        self._attr_icon = "mdi:battery-minus-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Registriert die Callback-Funktion zur Datenaktualisierung beim Hinzufügen zur Instanz.

        Verbindet die Entität mit einem Home Assistant Dispatcher, der beim Eintreffen
        neuer Sensordaten (`_handle_update`) aufgerufen wird.
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

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

    async def _handle_update(self, data):
        """Verarbeitet neue Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die vom Webhook empfangenen Sensordaten (inkl. PV-Leistung und Pccu).

        Berechnet die Batterieentladeleistung, wenn die Differenz zwischen PV-Leistung und
        Pccu negativ ist, und setzt den neuen Zustand der Entität.

        """
        ccu = float(data.get("Pccu", 0))

        if is_pccu_ok(ccu):
            pv_power = float(data.get("PV_power_total", 0))
            batteries = data.get("batteriesInfo", [])

            if is_power_total_ok(pv_power, batteries):
                batterie_leistung = round(pv_power - ccu, 3)

                if batterie_leistung <= 0:
                    self._attr_native_value = -1 * batterie_leistung
                else:
                    self._attr_native_value = 0

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
