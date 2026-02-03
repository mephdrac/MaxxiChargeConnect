"""Sensorentität für den Batterieladestrom (Battery Power Charge).

Diese Entität berechnet die aktuell in die Batterie eingespeiste Leistung auf Basis
der vom Webhook übermittelten Daten zu PV-Leistung und CCU-Verbrauch.

Funktionen:
    - Registriert sich bei einem Dispatcher-Signal, das bei neuen Webhook-Daten ausgelöst wird.
    - Führt eine Validierung durch (z.B. ob die Werte gültig sind) und berechnet die
      Batterieladeleistung.
    - Stellt die Sensoreigenschaften wie Einheit, Icon, Gerätetyp und Genauigkeit bereit.

Attribute:
    - Einheit: Watt
    - Gerätemodell: „CCU - Maxxicharge“
    - Symbol: mdi:battery-plus-variant

Wird die berechnete Leistung negativ, wird der Wert auf 0 gesetzt.

Hersteller: mephdrac
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


class BatteryPowerCharge(BaseWebhookSensor):
    """Sensorentität zur Anzeige der aktuellen Batterieladeleistung (Watt).

    Diese Entität berechnet die Ladeleistung basierend auf den aktuellen Daten
    vom PV-Wechselrichter und dem Stromverbrauch (Pccu). Wird der Sensor über
    einen Webhook mit aktualisierten Daten versorgt, wird die Ladeleistung als
    Differenz aus PV-Leistung und Pccu berechnet – jedoch nur, wenn die Differenz positiv ist.

    Die Entität registriert sich automatisch bei einem Dispatcher-Signal, das
    vom Webhook ausgelöst wird, um aktuelle Sensordaten zu erhalten.
    """

    _attr_translation_key = "BatteryPowerCharge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Battery Power Charge"
        self._attr_unique_id = f"{entry.entry_id}_battery_power_charge"
        self._attr_icon = "mdi:battery-plus-variant"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data):
        """Verarbeitet eingehende Sensordaten und aktualisiert den Zustand der Entität.

        Args:
            data (dict): Die vom Webhook empfangenen Rohdaten
            (z.B. 'Pccu', 'PV_power_total', 'batteriesInfo').

        Berechnet die Ladeleistung der Batterie als Differenz zwischen
        PV-Leistung und Verbrauch (Pccu). Negative Werte (Entladung) werden ignoriert.

        """
        try:
            # CCU-Verbrauch sicher abfragen
            pccu_raw = data.get("Pccu")
            if pccu_raw is None:
                _LOGGER.debug("BatteryPowerCharge: Pccu fehlt")
                return

            ccu = float(pccu_raw)

            if not is_pccu_ok(ccu):
                _LOGGER.warning(
                    "BatteryPowerCharge: PCCU-Wert nicht plausibel: %s W", ccu
                )
                return

            # PV-Leistung sicher abfragen
            pv_power_raw = data.get("PV_power_total")
            if pv_power_raw is None:
                _LOGGER.debug("BatteryPowerCharge: PV_power_total fehlt")
                return

            pv_power = float(pv_power_raw)
            batteries = data.get("batteriesInfo", [])

            if not is_power_total_ok(pv_power, batteries):
                _LOGGER.warning(
                    "BatteryPowerCharge: PV-Leistung nicht plausibel: %s W", pv_power
                )
                return

            # Ladeleistung berechnen
            battery_charge_power = round(pv_power - ccu, 3)

            # Nur positive Werte sind Ladeleistung
            if battery_charge_power > 0:
                self._attr_native_value = battery_charge_power
                _LOGGER.debug(
                    "BatteryPowerCharge: Ladeleistung berechnet: %s W (PV: %s W, CCU: %s W)",
                    battery_charge_power,
                    pv_power,
                    ccu,
                )
            else:
                _LOGGER.debug(
                    "BatteryPowerCharge: Keine Ladeleistung (PV: %s W, CCU: %s W, Differenz: %s W)",
                    pv_power,
                    ccu,
                    battery_charge_power,
                )
                return

        except (ValueError, TypeError) as err:
            _LOGGER.warning("BatteryPowerCharge: Konvertierungsfehler: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("BatteryPowerCharge: Unerwarteter Fehler: %s", err)
