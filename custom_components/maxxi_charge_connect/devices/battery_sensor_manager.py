"""Verwaltung dynamischer BatterySoESensor-Entitäten in MaxxiCharge Connect.

Dieses Modul enthält die BatterySensorManager-Klasse, die beim Eintreffen von
Webhook-Daten neue Sensoren für den State of Energy (SoE) von Batteriespeichern
erzeugt und registriert. Sensoren werden nur einmalig beim ersten Datenempfang
initialisiert und anschließend bei jedem Update aktualisiert.
"""

import logging
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
)  # noqa: TID252
from .battery_soe_sensor import BatterySoESensor

_LOGGER = logging.getLogger(__name__)


class BatterySensorManager:  # pylint: disable=too-few-public-methods
    """Manager zur dynamischen Erstellung und Verwaltung von BatterySoESensor-Entitäten.

    Erzeugt bei Empfang der ersten Daten automatisch eine Entität pro Batteriespeicher.
    Nach der Initialisierung werden alle zugehörigen Listener bei jedem weiteren
    Datenupdate über das Dispatcher-Signal informiert.
    """

    def __init__(self, hass: HomeAssistant, entry, async_add_entities) -> None:
        """Initialisiert den BatterySensorManager.

        Args:
            hass (HomeAssistant): Die Home Assistant Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            async_add_entities (Callable): Callback zum Hinzufügen neuer Entitäten.

        """
        self.hass = hass
        self.entry = entry
        self.async_add_entities = async_add_entities
        self.sensors: dict[str, BatterySoESensor] = {}
        self._registered = False

        self._enable_cloud_data = self.entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def setup(self):
        """Richtet den Dispatcher für eingehende Sensordaten ein.

        Erstellt den Listener auf das Dispatcher-Signal für diesen Konfigurationseintrag,
        um später automatisch neue Sensoren zu erzeugen und Daten zu verarbeiten.
        """

        entry_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(self.entry.entry_id, {})
        # Listener-Liste nur initialisieren, falls noch nicht vorhanden
        entry_data.setdefault("listeners", [])

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")

            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")
            signal = f"{DOMAIN}_{self.entry.data[CONF_WEBHOOK_ID]}_update_sensor"

            if not self._registered:
                async_dispatcher_connect(self.hass, signal, self._handle_update)
                self._registered = True

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self.entry.data.get(CONF_DEVICE_ID):
            await self._handle_update(json_data)

    async def _handle_update(self, data):
        batteries = data.get("batteriesInfo", [])

        # Initialisiere Sensoren, falls noch nicht vorhanden
        if not self.sensors and batteries:
            new_sensors = []
            for i in range(len(batteries)):
                unique_key = f"{self.entry.entry_id}_battery_soe_{i}"

                if unique_key not in self.sensors:
                    sensor = BatterySoESensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)
            if new_sensors:
                self.async_add_entities(new_sensors)

        # Update alle Sensoren
        # sichere Abfrage der Listener-Liste
        listeners = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {}).get("listeners", [])
        for listener in listeners:
            await listener(data)
