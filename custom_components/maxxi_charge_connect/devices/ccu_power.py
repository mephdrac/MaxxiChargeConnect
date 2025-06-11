"""Sensor-Entity zur Anzeige der aktuellen CCU-Leistung in Home Assistant.

Dieses Modul definiert die `CcuPower`-Klasse, die einen Sensor zur Messung der Leistung
(Pccu-Wert) einer CCU (Central Control Unit) bereitstellt. Die Daten werden per Webhook empfangen
und regelmäßig aktualisiert.

Die Klasse nutzt Home Assistants Dispatcher-System, um auf neue Sensordaten zu reagieren.
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

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from ..tools import isPccuOk  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class CcuPower(SensorEntity):
    """SensorEntity für die aktuelle CCU-Leistung (Pccu-Wert).

    Diese Entität zeigt die aktuell gemessene Leistung in Watt an,
    wenn die empfangenen Daten als gültig eingestuft werden.
    """

    _attr_translation_key = "CcuPower"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den CCU-Leistungssensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        self._unsub_dispatcher = None
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "CCU Power"
        self._attr_unique_id = f"{entry.entry_id}_ccu_power"
        self._attr_icon = "mdi:power-plug-battery-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Verbindet den Sensor mit dem Dispatcher-Signal zur Aktualisierung
        der Messwerte per Webhook.
        """

        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        """Wird beim Entfernen aus Home Assistant aufgerufen.

        Trennt die Verbindung zum Dispatcher-Signal.
        """
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Verarbeitet neue Webhook-Daten und aktualisiert den Sensorzustand.

        Und prüft auf Plausibilität.

        Args:
            data (dict): Die per Webhook empfangenen Sensordaten.

        """

        pccu = float(data.get("Pccu", 0))

        if isPccuOk(pccu):
            self._attr_native_value = float(data.get("Pccu", 0))
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
