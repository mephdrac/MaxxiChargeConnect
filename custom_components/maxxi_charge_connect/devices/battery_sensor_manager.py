"""Verwaltung dynamischer Battery-Sensoren in MaxxiCharge Connect.

Dieses Modul enthält die BatterySensorManager-Klasse, die beim Eintreffen von
Webhook-Daten neue Sensoren für verschiedene Batterie-Metriken erzeugt und registriert.
Sensoren werden nur einmalig beim ersten Datenempfang initialisiert und anschließend
bei jedem Update aktualisiert.
"""

import logging
from typing import Dict, List, Callable, Any
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
from .battery_pv_power_sensor import BatteryPVPowerSensor
from .battery_mppt_voltage_sensor import BatteryMpptVoltageSensor
from .battery_mppt_ampere_sensor import BatteryMpptAmpereSensor
from .battery_charge_sensor import BatteryChargeSensor
from .battery_discharge_sensor import BatteryDischargeSensor

_LOGGER = logging.getLogger(__name__)


class BatterySensorManager:  # pylint: disable=too-few-public-methods
    """Manager zur dynamischen Erstellung und Verwaltung von Battery-Sensoren.

    Erzeugt bei Empfang der ersten Daten automatisch eine Entität pro Batteriespeicher
    und pro Metrik. Nach der Initialisierung werden alle zugehörigen Listener bei jedem
    weiteren Datenupdate über das Dispatcher-Signal informiert.
    """

    # Sensor-Klassen für automatische Erstellung
    SENSOR_CLASSES = [
        ("battery_soe", BatterySoESensor),
        ("battery_soc_sensor", BatterySOCSensor),
        ("battery_voltage_sensor", BatteryVoltageSensor),
        ("battery_ampere_sensor", BatteryAmpereSensor),
        ("battery_pv_power_sensor", BatteryPVPowerSensor),
        ("battery_pv_voltage_sensor", BatteryPVVoltageSensor),
        ("battery_pv_ampere_sensor", BatteryPVAmpereSensor),
        ("battery_mppt_voltage_sensor", BatteryMpptVoltageSensor),
        ("battery_mppt_ampere_sensor", BatteryMpptAmpereSensor),
        ("battery_charge_sensor", BatteryChargeSensor),
        ("battery_discharge_sensor", BatteryDischargeSensor),
    ]

    def __init__(self, hass: HomeAssistant, entry, async_add_entities: Callable) -> None:
        """Initialisiert den BatterySensorManager.

        Args:
            hass (HomeAssistant): Die Home Assistant Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            async_add_entities (Callable): Callback zum Hinzufügen neuer Entitäten.

        """
        self.hass = hass
        self.entry = entry
        self.async_add_entities = async_add_entities
        self.sensors: Dict[str, SensorEntity] = {}
        self._registered = False
        self._unsub_update = None
        self._unsub_stale = None
        self._enable_cloud_data = self.entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def setup(self):
        """Richtet den Dispatcher für eingehende Sensordaten ein.

        Erstellt den Listener auf das Dispatcher-Signal für diesen Konfigurationseintrag,
        um später automatisch neue Sensoren zu erzeugen und Daten zu verarbeiten.
        """
        try:
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
                    _LOGGER.debug("BatterySensorManager Dispatcher registriert")
        except Exception as err:
            _LOGGER.error("Fehler beim Setup des BatterySensorManager: %s", err)

    async def _wrapper_update(self, data: dict):
        """Ablauf bei einem eingehenden Update-Event."""
        try:
            await self.handle_update(data)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fehler im BatterySensorManager beim Update: %s", err
            )

    async def _wrapper_stale(self, _):
        """Ablauf, wenn das Watchdog-Event 'stale' gesendet wird."""
        try:
            await self.handle_stale()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fehler im BatterySensorManager beim Stale-Handling: %s", err
            )

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""
        try:
            json_data = event.data.get("payload", {})

            if json_data.get(PROXY_ERROR_DEVICE_ID) == self.entry.data.get(CONF_DEVICE_ID):
                await self.handle_update(json_data)
        except Exception as err:
            _LOGGER.error("Fehler beim Proxy-Update: %s", err)

    async def handle_stale(self):
        """Setzt alle verwalteten Sensoren auf 'unavailable'."""
        _LOGGER.debug("Setze %d Sensoren auf unavailable", len(self.sensors))
        for sensor_key, sensor in self.sensors.items():
            try:
                if sensor is not None and sensor.hass is not None:
                    sensor._attr_available = False  # pylint: disable=protected-access
                    sensor._attr_state = STATE_UNKNOWN  # pylint: disable=protected-access
                    sensor.async_write_ha_state()
            except Exception as err:
                _LOGGER.warning(
                    "Fehler beim Setzen von Sensor %s auf unavailable: %s", 
                    sensor_key, err
                )

    async def handle_update(self, data: dict):
        """Behandelt eingehende Batteriedaten von der MaxxiCharge-Station.

        Args: 
            data (dict): Webhook-Daten, typischerweise mit `batteriesInfo`.
        """
        try:
            batteries = data.get("batteriesInfo", [])
            
            if not batteries:
                _LOGGER.debug("Keine Batterie-Informationen im Update")
                return

            # Initialisiere Sensoren, falls noch nicht vorhanden
            if not self.sensors:
                new_sensors = await self._create_sensors_for_batteries(batteries)
                if new_sensors:
                    _LOGGER.info(
                        "Erstelle %d neue Battery-Sensoren für %d Batterien", 
                        len(new_sensors), len(batteries)
                    )
                    await self.async_add_entities(new_sensors)

            # Update alle Sensoren über die Listener
            await self._update_all_listeners(data)
            
        except Exception as err:
            _LOGGER.error("Fehler bei der Verarbeitung der Battery-Daten: %s", err)

    async def _create_sensors_for_batteries(self, batteries: List[Dict[str, Any]]) -> List[SensorEntity]:
        """Erstellt Sensoren für alle Batterien.
        
        Args:
            batteries: Liste der Batterie-Informationen
            
        Returns:
            Liste der neu erstellten Sensoren
        """
        new_sensors = []
        
        try:
            for i in range(len(batteries)):
                for sensor_name, sensor_class in self.SENSOR_CLASSES:
                    unique_key = f"{self.entry.entry_id}_{sensor_name}_{i}"
                    
                    if unique_key not in self.sensors:
                        try:
                            _LOGGER.debug(
                                "Erstelle %s für Batterie %d", sensor_name, i
                            )
                            sensor = sensor_class(self.entry, i)
                            self.sensors[unique_key] = sensor
                            new_sensors.append(sensor)
                        except Exception as err:
                            _LOGGER.error(
                                "Fehler beim Erstellen von %s für Batterie %d: %s", 
                                sensor_name, i, err
                            )
                            
        except Exception as err:
            _LOGGER.error("Fehler bei der Sensor-Erstellung: %s", err)
            
        return new_sensors

    async def _update_all_listeners(self, data: dict):
        """Aktualisiert alle registrierten Listener.
        
        Args:
            data: Die zu verteilenden Update-Daten
        """
        try:
            # Sichere Abfrage der Listener-Liste
            listeners = (
                self.hass.data.get(DOMAIN, {})
                .get(self.entry.entry_id, {})
                .get("listeners", [])
            )
            
            _LOGGER.debug(
                "Verteile Update an %d Listener", len(listeners)
            )
            
            for listener in listeners:
                try:
                    await listener(data)
                except Exception as err:
                    _LOGGER.warning(
                        "Fehler beim Update eines Listeners: %s", err
                    )
                    
        except Exception as err:
            _LOGGER.error("Fehler beim Verteilen der Updates: %s", err)

    def get_sensor_count(self) -> int:
        """Gibt die Anzahl der verwalteten Sensoren zurück.
        
        Returns:
            Anzahl der Sensoren
        """
        return len(self.sensors)

    def get_sensor_info(self) -> Dict[str, str]:
        """Gibt Informationen über die verwalteten Sensoren zurück.
        
        Returns:
            Dictionary mit Sensor-Informationen
        """
        info = {}
        for key, sensor in self.sensors.items():
            try:
                info[key] = {
                    "class": sensor.__class__.__name__,
                    "available": getattr(sensor, "_attr_available", False),
                    "state": getattr(sensor, "_attr_native_value", None),
                }
            except Exception as err:
                info[key] = {"error": str(err)}
        return info
