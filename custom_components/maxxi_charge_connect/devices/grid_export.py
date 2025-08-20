"""Sensor-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert den `GridExport`-Sensor, der die aktuelle Einspeiseleistung
ins öffentliche Stromnetz misst und anzeigt. Der Sensor bezieht seine Daten über
einen Dispatcher-Signalmechanismus aus einem Webhook, der durch die Integration ausgelöst wird.

Die gemessene Leistung (`Pr`) wird auf ihre Plausibilität überprüft und in positiver Form
angezeigt, wenn eine tatsächliche Einspeisung stattfindet (d. h. `Pr < 0`).

Classes:
    GridExport: Sensor-Entity zur Darstellung der Netz-Einspeiseleistung in Watt.

Dependencies:
    - homeassistant.components.sensor
    - homeassistant.config_entries
    - homeassistant.const
    - homeassistant.helpers.dispatcher
    - .tools.isPrOk
    - .const.DEVICE_INFO, .const.DOMAIN
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
from ..tools import is_pr_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class GridExport(SensorEntity):
    """Sensor zur Anzeige der aktuellen Einspeiseleistung ins Netz.

    Dieser Sensor zeigt die aktuelle Leistung (in Watt) an, die ins Stromnetz
    eingespeist wird. Die Leistung wird als positiver Wert dargestellt,
    wenn Einspeisung erfolgt (Leistung < 0 im Eingangssignal).

    Attributes:
        _attr_translation_key (str): Schlüssel für die Übersetzung des Namens.
        _attr_has_entity_name (bool): Gibt an, dass die Entität einen eigenen Namen hat.

    Args:
        entry (ConfigEntry): Konfigurationseintrag der Integration.

    """

    _attr_translation_key = "GridExport"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den GridExport-Sensor.

        Args:
            entry (ConfigEntry): Konfigurationseintrag der Integration.

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Grid Export Power"
        self._attr_unique_id = f"{entry.entry_id}_grid_export"
        self._attr_icon = "mdi:transmission-tower-import"
        self._attr_native_value = None

        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird.

        Registriert den Dispatcher-Signal-Listener für Updates.
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
        """Verarbeitet eingehende Sensordaten vom Dispatcher.

        Args:
            data (dict): Datenpaket mit Messwerten, erwartet Schlüssel 'Pr'.

        Setzt den aktuellen Wert auf die positive Einspeiseleistung in Watt,
        falls der Wert plausibel ist.

        """

        pr = float(data.get("Pr", 0))
        if is_pr_ok(pr):
            self._attr_native_value = round(max(-pr, 0), 2)
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
