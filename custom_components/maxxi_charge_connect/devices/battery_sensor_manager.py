"""Verwaltung dynamischer BatterySoESensor-Entitäten in MaxxiCharge Connect.

Dieses Modul enthält die BatterySensorManager-Klasse, die beim Eintreffen von
Webhook-Daten neue Sensoren für den State of Energy (SoE) von Batteriespeichern
erzeugt und registriert. Sensoren werden nur einmalig beim ersten Datenempfang
initialisiert und anschließend bei jedem Update aktualisiert.
"""

import logging
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DOMAIN
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

    async def setup(self):
        """Richtet den Dispatcher für eingehende Sensordaten ein.

        Erstellt den Listener auf das Dispatcher-Signal für diesen Konfigurationseintrag,
        um später automatisch neue Sensoren zu erzeugen und Daten zu verarbeiten.
        """
        signal = f"{DOMAIN}_{self.entry.data[CONF_WEBHOOK_ID]}_update_sensor"
        self.hass.data.setdefault(DOMAIN, {}).setdefault(self.entry.entry_id, {})
        self.hass.data[DOMAIN][self.entry.entry_id]["listeners"] = []
        if not self._registered:
            async_dispatcher_connect(self.hass, signal, self._handle_update)
            self._registered = True

    async def _handle_update(self, data):
        batteries = data.get("batteriesInfo", [])
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
        for listener in self.hass.data[DOMAIN][self.entry.entry_id]["listeners"]:
            await listener(data)
