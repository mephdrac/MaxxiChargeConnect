"""Sensor zur Anzeige der aktuellen Photovoltaik-Leistung (PV Power).

Dieser Sensor visualisiert den aktuellen Gesamtwert der erzeugten Leistung
aus allen PV-Modulen, wie er vom MaxxiCharge-System bereitgestellt wird.
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
from ..tools import isPowerTotalOk  # noqa: TID252


class PvPower(SensorEntity):
    """Sensor-Entität zur Anzeige der PV-Gesamtleistung (`PV_power_total`)."""

    _attr_translation_key = "PvPower"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für PV-Leistung.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        self._unsub_dispatcher = None
        self._entry = entry
        # self._attr_name = "PV Power"
        self._attr_unique_id = f"{entry.entry_id}_pv_power"
        self._attr_icon = "mdi:solar-power"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def async_added_to_hass(self):
        """Registriert den Sensor im Home Assistant Event-System.

        Verbindet sich mit dem Dispatcher, um auf Webhook-Updates zu reagieren.
        """
        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        """Wird aufgerufen, wenn die Entität entfernt wird.

        Trennt die Verbindung zum Signal-Dispatcher.
        """
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Behandelt eingehende Leistungsdaten von der MaxxiCharge-Station.

        Args:
            data (dict): Webhook-Daten, typischerweise mit `PV_power_total`
                         und `batteriesInfo`.

        """
        pv_power = float(data.get("PV_power_total", 0))
        batteries = data.get("batteriesInfo", [])

        if isPowerTotalOk(pv_power, batteries):
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
