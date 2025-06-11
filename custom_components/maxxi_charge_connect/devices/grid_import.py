"""Sensor zur Messung der aktuellen Netzimportleistung für Home Assistant.

Dieses Modul definiert die Entität `GridImport`, die die vom Stromnetz
importierte Leistung (in Watt) darstellt. Die Werte werden per Webhook übermittelt
und bei neuen Daten aktualisiert.
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


class GridImport(SensorEntity):
    """Sensor-Entität für importierte Leistung aus dem Stromnetz (Grid Import).

    Diese Entität empfängt Leistungsdaten über einen internen Dispatcher
    (z.B. ausgelöst durch einen Webhook) und aktualisiert den aktuellen
    Leistungswert (Watt).
    """

    _attr_translation_key = "GridImport"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die GridImport-Sensor-Entität.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für die Integration.

        """
        self._unsub_dispatcher = None
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Grid Import Power"
        self._attr_unique_id = f"{entry.entry_id}_grid_import"
        self._attr_icon = "mdi:transmission-tower-export"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def async_added_to_hass(self):
        """Registriert Callback, wenn die Entität zu Home Assistant hinzugefügt wurde.

        Verbindet sich mit einem Dispatcher-Signal, um Sensordaten zu empfangen.
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

        Trennt die Verbindung zum Dispatcher.
        """
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Verarbeitet eingehende Leistungsdaten.

        Args:
            data (dict): Ein Dictionary mit Sensordaten, typischerweise aus einem Webhook.
                         Erwartet den Schlüssel `"Pr"` für Netzimport-Leistung (W).

        """
        pr = float(data.get("Pr", 0))
        if isPrOk(pr):
            self._attr_native_value = max(pr, 0)
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
