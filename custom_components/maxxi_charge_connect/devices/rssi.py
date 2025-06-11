"""Sensor für die WLAN-Signalstärke.

Dieses Modul enthält die Klasse Rssi, die einen Sensor für die WLAN-Signalstärke (RSSI)
innerhalb der Home Assistant Integration bereitstellt.
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_WEBHOOK_ID,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252


class Rssi(SensorEntity):
    """SensorEntity zur Messung der WLAN-Signalstärke (RSSI).

    Attributes:
        _attr_entity_registry_enabled_default (bool): Gibt an, ob die Entität standardmäßig
          im Entity Registry aktiviert ist (hier False).
        _attr_translation_key (str): Übersetzungsschlüssel für den Namen.
        _attr_has_entity_name (bool): Gibt an, ob die Entität einen eigenen Namen hat.
        _unsub_dispatcher: Callback zum Abbestellen der Dispatcher-Signale.
        _entry (ConfigEntry): Die ConfigEntry der Integration.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den RSSI Sensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag der Integration.

        """
        self._unsub_dispatcher = None
        self._entry = entry
        # self._attr_name = "Rssi"
        self._attr_unique_id = f"{entry.entry_id}_rssi"
        self._attr_icon = "mdi:wifi"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entity zu Home Assistant hinzugefügt wird.

        Registriert sich beim Dispatcher, um Updates zur Signalstärke zu empfangen.
        """
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )
        self.async_on_remove(self._unsub_dispatcher)

    async def async_will_remove_from_hass(self):
        """Wird aufgerufen, wenn die Entity aus Home Assistant entfernt wird.

        Hebt die Registrierung beim Dispatcher auf, um Speicherlecks zu vermeiden.
        """
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Wird aufgerufen, beim Empfang neuer Daten vom Dispatcher.

        Aktualisiert den aktuellen Wert des Sensors mit der neuen Signalstärke.

        Args:
            data (dict): Ein Dictionary, das die neuen Sensordaten enthält,
                         insbesondere der Schlüssel 'wifiStrength' mit dem Wert der Signalstärke.

        """

        self._attr_native_value = data.get("wifiStrength")
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
