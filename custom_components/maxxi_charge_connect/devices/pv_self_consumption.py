"""Sensor zur Anzeige des aktuellen PV-Eigenverbrauchs.

Dieser Sensor zeigt die aktuell selbst genutzte Photovoltaik-Leistung an,
basierend auf der Differenz zwischen erzeugter PV-Leistung und Rückeinspeisung.
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
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
from ..tools import is_power_total_ok, is_pr_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class PvSelfConsumption(SensorEntity):
    """Sensor-Entität zur Anzeige des PV-Eigenverbrauchs (PV Self-Consumption)."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "PvSelfConsumption"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den PV-Eigenverbrauchs-Sensor.

        Args:
            entry (ConfigEntry): Die Konfiguration der Integration.

        """
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "PV Self-Consumption"
        self._attr_unique_id = f"{entry.entry_id}_pv_consumption"
        self._attr_icon = "mdi:solar-power-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """Registriert den Sensor beim Hinzufügen zu Home Assistant.

        Verbindet den Sensor mit dem Dispatcher zur Verarbeitung eingehender Webhook-Daten.
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
        """Verarbeitet neue Leistungsdaten zur Berechnung des PV-Eigenverbrauchs.

        Die Berechnung erfolgt nach der Formel:
        `PV_power_total - max(-Pr, 0)`, wobei Pr der Rückspeisewert ist.

        Args:
            data (dict): Die vom Webhook gesendeten Sensordaten.

        """

        pv_power = float(data.get("PV_power_total", 0))
        batteries = data.get("batteriesInfo", [])

        if is_power_total_ok(pv_power, batteries):
            pr = float(data.get("Pr", 0))

            if is_pr_ok(pr):
                self._attr_native_value = pv_power - max(-pr, 0)
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
