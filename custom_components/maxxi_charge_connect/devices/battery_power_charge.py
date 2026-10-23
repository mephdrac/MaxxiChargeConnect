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

from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252
from ..const import CONF_CCU_VERSION, CCU_V1, CCU_V2
from .base_webhook_sensor import BaseWebhookSensor

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

    async def handle_update(self, data: dict) -> None:
        """Update battery charging power for CCU V1 and V2."""

        try:
            ccu_version = self._entry.data.get(
                CONF_CCU_VERSION,
                CCU_V1,
            )

            pv_power_raw = data.get("PV_power_total")

            if pv_power_raw is None:
                _LOGGER.debug("BatteryPowerCharge: PV_power_total fehlt")
                return

            pv_power = float(pv_power_raw)

            if ccu_version == CCU_V2:
                # CCU V2: Vorzeichenbehaftete Wechselrichterleistung
                inverter_power_raw = data.get("InverterPowerSigned")

                if inverter_power_raw is None:
                    _LOGGER.debug(
                        "BatteryPowerCharge: InverterPowerSigned fehlt"
                    )
                    return

                inverter_power = float(inverter_power_raw)

                # Positiv: Einspeisung ins Hausnetz
                # Negativ: Netzbezug der CCU
                battery_charge_power = max(
                    pv_power - inverter_power,
                    0,
                )

            else:
                # CCU V1: Bisherige Berechnung beibehalten
                pccu_raw = data.get("Pccu")

                if pccu_raw is None:
                    _LOGGER.debug("BatteryPowerCharge: Pccu fehlt")
                    return

                ccu = float(pccu_raw)

                if not is_pccu_ok(ccu):
                    _LOGGER.warning(
                        "BatteryPowerCharge: Pccu unplausibel: %s W",
                        ccu,
                    )
                    return

                batteries = data.get("batteriesInfo", [])

                if not is_power_total_ok(pv_power, batteries):
                    _LOGGER.warning(
                        "BatteryPowerCharge: PV-Leistung unplausibel: %s W",
                        pv_power,
                    )
                    return

                battery_charge_power = max(
                    pv_power - ccu,
                    0,
                )

            self._attr_native_value = round(
                battery_charge_power,
                2,
            )

            _LOGGER.debug(
                "BatteryPowerCharge (%s): PV=%s W, Ladeleistung=%s W",
                ccu_version,
                pv_power,
                self._attr_native_value,
            )

        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPowerCharge: Ungültige Leistungsdaten: %s",
                err,
            )