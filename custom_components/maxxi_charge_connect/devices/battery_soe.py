"""Dieses Modul definiert die Sensor-Entity `BatterySoE`.

Die Entity stellt den aktuellen „State of Energy" (SoE) des Batteriesystems
dar und aktualisiert ihren Zustand dynamisch anhand von empfangenen Sensordaten.

Die Klasse `BatterySoE` erbt von `BaseWebhookSensor` und implementiert alle nötigen Methoden für die
Integration in Home Assistant, inklusive Registrierung von Updates über Dispatcher-Signale
und Geräteinformationen.

Konstanten:
    - DOMAIN: Die Domain der Integration, z.B. "maxxi_charge_connect".

"""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class BatterySoE(BaseWebhookSensor):
    """SensorEntity zur Darstellung des Batteriezustands in Wattstunden (State of Energy).

    Dieser Sensor zeigt die Gesamtkapazität aller Batterien im System an.
    Die Daten werden von den Batterieinformationen im Webhook-Datenstrom extrahiert
    und auf Plausibilität geprüft.

    Attribute:
        _attr_suggested_display_precision (int): Vorgeschlagene Genauigkeit für Anzeige.
        _entry (ConfigEntry): Referenz auf den ConfigEntry dieser Instanz.
        _attr_unique_id (str): Eindeutige ID der Entity.
        _attr_icon (str): Icon für die Entity im Frontend.
        _attr_native_value (float|None): Aktueller State of Energy-Wert.
        _attr_device_class (SensorDeviceClass): Device Class für Energiespeicher.
        _attr_native_unit_of_measurement (str): Einheit der Messgröße (Wh).

    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "BatterySoE"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die BatterySoE Sensor-Entity mit den Grundeinstellungen.

        Args:
            entry (ConfigEntry): Konfigurationseintrag mit den Nutzereinstellungen.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_soe"
        self._attr_icon = "mdi:home-battery"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    async def handle_update(self, data):
        """Aktualisiert den State of Energy anhand der empfangenen Sensordaten.

        Args:
            data (dict): Aktuelle Sensordaten mit Batteriesystem-Informationen.

        """
        try:
            batteries_info = data.get("batteriesInfo", [])
            
            if not batteries_info or not isinstance(batteries_info, list):
                _LOGGER.debug("BatterySoE: batteriesInfo leer oder keine Liste")
                return

            total_capacity = 0.0
            valid_batteries = 0
            
            for i, battery in enumerate(batteries_info):
                if not isinstance(battery, dict):
                    _LOGGER.debug("BatterySoE: Batterie %s ist kein Dictionary", i)
                    continue
                    
                capacity_raw = battery.get("batteryCapacity")
                if capacity_raw is None:
                    _LOGGER.debug("BatterySoE: batteryCapacity fehlt bei Batterie %s", i)
                    continue
                
                try:
                    capacity = float(capacity_raw)
                    
                    # Plausibilitätsprüfung für einzelne Batterie
                    if capacity < 0:
                        _LOGGER.warning("BatterySoE: Negative Kapazität bei Batterie %s: %s Wh", i, capacity)
                        continue
                    
                    if capacity > 100000:  # Max 100 kWh pro Batterie
                        _LOGGER.warning("BatterySoE: Kapazität zu hoch bei Batterie %s: %s Wh", i, capacity)
                        continue
                    
                    total_capacity += capacity
                    valid_batteries += 1
                    
                except (ValueError, TypeError) as err:
                    _LOGGER.warning("BatterySoE: Konvertierungsfehler bei Batterie %s: %s", i, err)
                    continue

            # Plausibilitätsprüfung für Gesamtkapazität
            if total_capacity < 0:
                _LOGGER.warning("BatterySoE: Negative Gesamtkapazität: %s Wh", total_capacity)
                return
            
            if total_capacity > 500000:  # Max 500 kWh für Gesamtsystem
                _LOGGER.warning("BatterySoE: Gesamtkapazität unrealistisch: %s Wh", total_capacity)
                return

            self._attr_native_value = total_capacity
            
            _LOGGER.debug(
                "BatterySoE: Aktualisiert auf %s Wh (%s gültige Batterien)", 
                total_capacity, valid_batteries
            )
            
        except Exception as err:
            _LOGGER.error("BatterySoE: Fehler bei der Verarbeitung: %s", err)
