"""Sensor zur Darstellung der Momentanleistung am Netzanschlusspunkt (PowerMeter).

Dieser Sensor zeigt den aktuell gemessenen Wert von `Pr` an, also die
Import-/Exportleistung am Netzanschlusspunkt, wie sie vom MaxxiCharge-Gerät
geliefert wird.
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from ..tools import isPrOk  # noqa: TID252


class PowerMeter(SensorEntity):
    """Sensor-Entität zur Anzeige der Rohleistung (`Pr`) am Hausanschluss in Watt."""

    _attr_translation_key = "PowerMeter"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den PowerMeter-Sensor mit den Basisattributen.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz, die vom Benutzer gesetzt wurde.

        """
        self._unsub_dispatcher = None
        self._attr_suggested_display_precision = 2
        self._entry = entry
        #    self._attr_name = "Power Meter"
        self._attr_unique_id = f"{entry.entry_id}_power_meter"
        self._attr_icon = "mdi:gauge"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird.

        Verbindet sich mit dem Dispatcher, um bei Webhook-Updates aktualisiert zu werden.
        """
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        """Wird aufgerufen, bevor die Entität aus Home Assistant entfernt wird.

        Trennt die Verbindung zum Dispatcher, um Ressourcen freizugeben.
        """

        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Behandelt eingehende Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Dictionary mit dem Schlüssel `Pr`, der die momentane
                         Import-/Exportleistung repräsentiert.

        """
        pr = data.get("Pr")

        if isPrOk(pr):
            self._attr_native_value = pr
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
