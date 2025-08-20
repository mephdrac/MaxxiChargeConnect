"""Sensorentität für den Batterieladestrom (Battery Power Charge).

Diese Entität berechnet die aktuell in die Batterie eingespeiste Leistung auf Basis
der vom Webhook übermittelten Daten zu PV-Leistung und CCU-Verbrauch.

Funktionen:
    - Registriert sich bei einem Dispatcher-Signal, das bei neuen Webhook-Daten ausgelöst wird.
    - Führt eine Validierung durch (z.B. ob die Werte gültig sind) und berechnet die
      Batterieladeleistung.
    - Stellt die Sensoreigenschaften wie Einheit, Icon, Gerätetyp und Genauigkeit bereit.

Attribute:
    - Einheit: Watt
    - Gerätemodell: „CCU - Maxxicharge“
    - Symbol: mdi:battery-plus-variant

Wird die berechnete Leistung negativ, wird der Wert auf 0 gesetzt.

Hersteller: mephdrac
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

from ..const import (
    DEVICE_INFO,
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryPowerCharge(SensorEntity):
    """Sensorentität zur Anzeige der aktuellen Batterieladeleistung (Watt).

    Diese Entität berechnet die Ladeleistung basierend auf den aktuellen Daten
    vom PV-Wechselrichter und dem Stromverbrauch (Pccu). Wird der Sensor über
    einen Webhook mit aktualisierten Daten versorgt, wird die Ladeleistung als
    Differenz aus PV-Leistung und Pccu berechnet – jedoch nur, wenn die Differenz positiv ist.

    Die Entität registriert sich automatisch bei einem Dispatcher-Signal, das
    vom Webhook ausgelöst wird, um aktuelle Sensordaten zu erhalten.
    """

    _attr_translation_key = "BatteryPowerCharge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Battery Power Charge"
        self._attr_unique_id = f"{entry.entry_id}_battery_power_charge"
        self._attr_icon = "mdi:battery-plus-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wurde.

        Registriert die Entität bei einem Dispatcher-Signal, um auf
        Webhook-Datenaktualisierungen zu reagieren.
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
        """Verarbeitet eingehende Sensordaten und aktualisiert den Zustand der Entität.

        Args:
            data (dict): Die vom Webhook empfangenen Rohdaten
            (z.B. 'Pccu', 'PV_power_total', 'batteriesInfo').

        Berechnet die Ladeleistung der Batterie als Differenz zwischen
        PV-Leistung und Verbrauch (Pccu). Negative Werte (Entladung) werden auf 0 gesetzt.

        """

        ccu = float(data.get("Pccu", 0))

        if is_pccu_ok(ccu):
            pv_power = float(data.get("PV_power_total", 0))
            batteries = data.get("batteriesInfo", [])

            if is_power_total_ok(pv_power, batteries):
                batterie_leistung = round(pv_power - ccu, 3)

                if batterie_leistung >= 0:
                    self._attr_native_value = batterie_leistung
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
