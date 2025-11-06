"""Verwaltung dynamischer BatterySoESensor-Entitäten in MaxxiCharge Connect.

Dieses Modul enthält die BatterySensorManager-Klasse, die beim Eintreffen von
Webhook-Daten neue Sensoren für den State of Energy (SoE) von Batteriespeichern
erzeugt und registriert. Sensoren werden nur einmalig beim ersten Datenempfang
initialisiert und anschließend bei jedem Update aktualisiert.
"""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DOMAIN,
    PROXY_STATUS_EVENTNAME,
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
    WEBHOOK_SIGNAL_UPDATE,
    WEBHOOK_SIGNAL_STATE,
)  # noqa: TID252
from .battery_soe_sensor import BatterySoESensor
from .battery_soc_sensor import BatterySOCSensor
from .battery_voltage_sensor import BatteryVoltageSensor
from .battery_ampere_sensor import BatteryAmpereSensor
from .battery_pv_voltage_sensor import BatteryPVVoltageSensor
from .battery_pv_ampere_sensor import BatteryPVAmpereSensor
from .battery_mppt_voltage_sensor import BatteryMpptVoltageSensor
from .battery_mppt_ampere_sensor import BatteryMpptAmpereSensor
from .battery_charge_sensor import BatteryChargeSensor
from .battery_discharge_sensor import BatteryDischargeSensor

_LOGGER = logging.getLogger(__name__)


class BatterySensorManager:  # pylint: disable=too-few-public-methods, too-many-branches, too-many-statements
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
        self.sensors: dict[str, SensorEntity] = {}
        self._registered = False
        self._unsub_update = None
        self._unsub_stale = None
        self._enable_cloud_data = self.entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def setup(self):
        """Richtet den Dispatcher für eingehende Sensordaten ein.

        Erstellt den Listener auf das Dispatcher-Signal für diesen Konfigurationseintrag,
        um später automatisch neue Sensoren zu erzeugen und Daten zu verarbeiten.
        """

        entry_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            self.entry.entry_id, {}
        )
        # Listener-Liste nur initialisieren, falls noch nicht vorhanden
        entry_data.setdefault("listeners", [])

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")

            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            _LOGGER.info("Daten kommen vom Webhook")
            entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
            update_signal = entry_data[WEBHOOK_SIGNAL_UPDATE]
            stale_signal = entry_data[WEBHOOK_SIGNAL_STATE]

            if not self._registered:
                self._unsub_update = async_dispatcher_connect(
                    self.hass, update_signal, self._wrapper_update
                )

                self._unsub_stale = async_dispatcher_connect(
                    self.hass, stale_signal, self._wrapper_stale
                )
                self._registered = True

    async def _wrapper_update(self, data: dict):
        """Ablauf bei einem eingehenden Update-Event."""
        try:
            await self.handle_update(data)
            # self._attr_available = True
            # self.async_write_ha_state()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fehler im Sensor %s beim Update: %s", self.__class__.__name__, err
            )

    async def _wrapper_stale(self, _):
        """Ablauf, wenn das Watchdog-Event 'stale' gesendet wird."""
        await self.handle_stale()
        # self.async_write_ha_state()

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self.entry.data.get(CONF_DEVICE_ID):
            await self.handle_update(json_data)

    async def handle_stale(self):
        """Setzt alle verwalteten Sensoren auf 'unavailable'."""
        for sensor in self.sensors.values():
            sensor._attr_available = False  # pylint: disable=protected-access
            sensor._attr_state = STATE_UNKNOWN  # pylint: disable=protected-access
            sensor.async_write_ha_state()

    async def handle_update(self, data):
        """Behandelt eingehende Batteriedaten von der MaxxiCharge-Station.

        Args: data (dict): Webhook-Daten, typischerweise mit `batteriesInfo`.
        """
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

                unique_key = f"{self.entry.entry_id}_battery_soc_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatterySOCSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_voltage_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryVoltageSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_ampere_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryAmpereSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_pv_voltage_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryPVVoltageSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_pv_ampere_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryPVAmpereSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_mppt_voltage_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryMpptVoltageSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_mppt_ampere_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryMpptAmpereSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_charge_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryChargeSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

                unique_key = f"{self.entry.entry_id}_battery_discharge_sensor_{i}"
                if unique_key not in self.sensors:
                    sensor = BatteryDischargeSensor(self.entry, i)
                    self.sensors[unique_key] = sensor
                    new_sensors.append(sensor)

            if new_sensors:
                self.async_add_entities(new_sensors)

        # Update alle Sensoren
        # sichere Abfrage der Listener-Liste
        listeners = (
            self.hass.data.get(DOMAIN, {})
            .get(self.entry.entry_id, {})
            .get("listeners", [])
        )
        for listener in listeners:
            await listener(data)
