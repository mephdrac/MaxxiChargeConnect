"""Sensor zur Anzeige der CCU-Temperatur."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, EntityCategory

from .base_webhook_sensor import BaseWebhookSensor

_LOGGER = logging.getLogger(__name__)


class CCUTemperaturSensor(BaseWebhookSensor):
    """Sensor-Entität zur Anzeige der CCU-Temperatur.

    Dieser Sensor zeigt die durchschnittliche Temperatur aller CCU-Converter an.
    Die Daten werden von den Converter-Informationen im Webhook-Datenstrom extrahiert
    und auf Plausibilität geprüft.
    """

    _attr_translation_key = "CCUTemperaturSensor"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den Sensor für CCU-Temperatur.

        Args:
            entry (ConfigEntry): Die Konfigurationsinstanz für diese Integration.

        """
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ccu_temperatur_sensor"
        self._attr_icon = "mdi:temperature-celsius"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def handle_update(self, data):
        """Behandelt CCU-Temperaturen vom MaxxiCharge.

        Args:
            data (dict): Die empfangenen Webhook-Daten.

        """
        try:
            if not data or "convertersInfo" not in data:
                _LOGGER.debug("Keine convertersInfo für CCU-Temperatur vorhanden")
                self._attr_native_value = None
                return

            converters_info = data.get("convertersInfo", [])
            if not converters_info:
                _LOGGER.debug("convertersInfo ist leer")
                self._attr_native_value = None
                return

            ccu_temperaturen = []
            valid_converters = 0

            for i, conv in enumerate(converters_info):
                if not isinstance(conv, dict):
                    _LOGGER.debug("Converter %s ist kein Dictionary", i)
                    continue

                temp_raw = conv.get("ccuTemperature")
                if temp_raw is None:
                    _LOGGER.debug("ccuTemperature fehlt bei Converter %s", i)
                    continue

                try:
                    temperature = float(temp_raw)
                    
                    # Plausibilitätsprüfung: Temperatur sollte im vernünftigen Bereich liegen
                    if not (-40 <= temperature <= 85):
                        _LOGGER.warning(
                            "Unplausible CCU-Temperatur bei Converter %s: %s°C", 
                            i, temperature
                        )
                        continue
                    
                    ccu_temperaturen.append(temperature)
                    valid_converters += 1
                    
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Konvertierungsfehler bei Converter %s: %s", 
                        i, err
                    )
                    continue

            if not ccu_temperaturen:
                _LOGGER.debug("Keine gültigen CCU-Temperaturen gefunden")
                self._attr_native_value = None
                return

            # Durchschnitt berechnen
            durchschnitt = sum(ccu_temperaturen) / len(ccu_temperaturen)
            
            # Plausibilitätsprüfung für Durchschnitt
            if not (-40 <= durchschnitt <= 85):
                _LOGGER.warning(
                    "Unplausible durchschnittliche CCU-Temperatur: %s°C", 
                    durchschnitt
                )
                self._attr_native_value = None
                return

            self._attr_native_value = round(durchschnitt, 1)
            _LOGGER.debug(
                "CCU-Temperatur aktualisiert: %s°C (%s gültige Converter)", 
                self._attr_native_value, valid_converters
            )
            
        except Exception as err:
            _LOGGER.error("Fehler bei der Verarbeitung der CCU-Temperatur: %s", err)
            self._attr_native_value = None
