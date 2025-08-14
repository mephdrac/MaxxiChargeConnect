"""Sensor-Entity zur Darstellung der Batterieleistung für MaxxiChargeConnect.

Dieses Modul definiert die Klasse BatteryPower, eine Home Assistant SensorEntity,
die die aktuelle Batterieleistung basierend auf den eingehenden Webhook-Daten
überwacht und darstellt.

Die Sensor-Entity:
    - Abonniert Webhook-Updates über den Dispatcher.
    - Validiert empfangene Werte mittels externer Hilfsfunktionen.
    - Berechnet die Batterieleistung aus der PV-Leistung und dem CCU-Wert.
    - Aktualisiert den Sensorwert und stellt ihn in Watt dar.

Die Entity ist für die automatische Anzeige in Home Assistant konfiguriert
und besitzt ein eindeutiges Entity-ID-Schema basierend auf dem ConfigEntry.

Abhängigkeiten:
    - homeassistant.components.sensor
    - homeassistant.config_entries
    - homeassistant.helpers.dispatcher
    - custom_components.maxxi_charge_connect.tools (für Validierungshilfen)

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
from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryPower(SensorEntity):
    """Sensor zur Überwachung und Anzeige der Batterieleistung.

    Diese Klasse implementiert eine Home Assistant SensorEntity, die
    Batterieleistung in Watt basierend auf eingehenden Webhook-Daten misst.

    Attributes:
        _entry (ConfigEntry): Der zugehörige ConfigEntry.
        _unsub_dispatcher (callable | None): Funktion zum Abbestellen des Dispatchersignals.

    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "battery_power"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die BatteryPower Sensor-Entität.

        Args:
            entry (ConfigEntry): Der ConfigEntry, der die Konfiguration für diese Instanz enthält.

            Initialisiert die wichtigsten Entity-Attribute wie eindeutige ID, Icon,
            Einheit, Gerätetyp und vorgeschlagene Genauigkeit für die Anzeige.

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Battery Power"
        self._attr_unique_id = f"{entry.entry_id}_battery_power"
        self._attr_icon = "mdi:battery-charging-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Registriert den Dispatcher-Listener beim Hinzufügen zur Home Assistant Instanz.

        Diese Methode wird automatisch aufgerufen, wenn die Entity zur
        Home Assistant Instanz hinzugefügt wird.

        Registriert eine Callback-Funktion, die auf eingehende Webhook-Daten hört.
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
        """Verarbeitet empfangene Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen JSON-Daten vom Webhook.

        Validiert die eingehenden Werte mit Hilfsfunktionen und berechnet
        die Batterieleistung. Aktualisiert dann den Sensorstatus.

        """

        ccu = float(data.get("Pccu", 0))

        if is_pccu_ok(ccu):
            pv_power = float(data.get("PV_power_total", 0))
            batteries = data.get("batteriesInfo", [])

            if is_power_total_ok(pv_power, batteries):
                batterie_leistung = round(pv_power - ccu, 3)

                self._attr_native_value = batterie_leistung
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
