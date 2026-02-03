"""Sensorentität zur Darstellung der Batterieentladeleistung für MaxxiCharge.

Dieses Modul definiert die `BatteryPowerDischarge`-Entität, die in Home Assistant
eingebunden wird, um den Entladestrom der Batterie basierend auf Daten aus einem
Webhook zu visualisieren. Sie aktualisiert sich automatisch bei eingehendem Signal
und nutzt standardisierte Sensor-Attribute wie Leistungseinheit, Geräteklasse und
Zustandsklasse.
"""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from .base_webhook_sensor import BaseWebhookSensor

from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class BatteryPowerDischarge(BaseWebhookSensor):
    """Sensorentität zur Anzeige der aktuellen Batterieentladeleistung (Watt).

    Diese Entität berechnet die Entladeleistung der Batterie basierend auf der
    Differenz zwischen Photovoltaik-Leistung (PV_power_total) und dem Stromverbrauch
    (Pccu). Wenn die Differenz negativ ist, wird die absolute Differenz als
    Entladeleistung interpretiert – ansonsten wird 0 angezeigt.

    Die Entität registriert sich bei einem Dispatcher-Signal, das über einen
    Webhook mit aktuellen Leistungsdaten versorgt wird, und aktualisiert sich
    entsprechend.

    Die Entität wird standardmäßig im Entity-Registry aktiviert und nutzt
    standardisierte Geräteeigenschaften für Darstellung und Klassifikation.
    """

    _attr_translation_key = "BatteryPowerDischarge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Sensor-Entität.

        Args:
            entry (ConfigEntry): Die Konfigurationsdaten dieser Instanz.

        Setzt die Geräteattribute wie Icon, Einheit, Gerätetyp und eindeutige ID.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._entry = entry
        #    self._attr_name = "Battery Power Discharge"
        self._attr_unique_id = f"{entry.entry_id}_battery_power_discharge"
        self._attr_icon = "mdi:battery-minus-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet neue Leistungsdaten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die vom Webhook empfangenen Sensordaten (inkl. PV-Leistung und Pccu).

        Berechnet die Batterieentladeleistung, wenn die Differenz zwischen PV-Leistung und
        Pccu negativ ist, und setzt den neuen Zustand der Entität.

        """
        try:
            # CCU-Verbrauch sicher abfragen
            pccu_raw = data.get("Pccu")
            if pccu_raw is None:
                _LOGGER.debug("BatteryPowerDischarge: Pccu fehlt")
                return
            
            ccu = float(pccu_raw)
            
            if not is_pccu_ok(ccu):
                _LOGGER.warning("BatteryPowerDischarge: PCCU-Wert nicht plausibel: %s W", ccu)
                return

            # PV-Leistung sicher abfragen
            pv_power_raw = data.get("PV_power_total")
            if pv_power_raw is None:
                _LOGGER.debug("BatteryPowerDischarge: PV_power_total fehlt")
                return
            
            pv_power = float(pv_power_raw)
            batteries = data.get("batteriesInfo", [])

            if not is_power_total_ok(pv_power, batteries):
                _LOGGER.warning("BatteryPowerDischarge: PV-Leistung nicht plausibel: %s W", pv_power)
                return

            # Entladeleistung berechnen
            battery_discharge_power = round(pv_power - ccu, 3)
            
            # Nur negative Werte sind Entladeleistung
            if battery_discharge_power < 0:
                discharge_power = abs(battery_discharge_power)
                self._attr_native_value = discharge_power
                _LOGGER.debug(
                    "BatteryPowerDischarge: Entladeleistung berechnet: %s W (PV: %s W, CCU: %s W)", 
                    discharge_power, pv_power, ccu
                )
            else:
                _LOGGER.debug(
                    "BatteryPowerDischarge: Keine Entladeleistung (PV: %s W, CCU: %s W, Differenz: %s W)", 
                    pv_power, ccu, battery_discharge_power
                )
                return
            
        except (ValueError, TypeError) as err:
            _LOGGER.warning("BatteryPowerDischarge: Konvertierungsfehler: %s", err)
        except Exception as err:
            _LOGGER.error("BatteryPowerDischarge: Unerwarteter Fehler: %s", err)
