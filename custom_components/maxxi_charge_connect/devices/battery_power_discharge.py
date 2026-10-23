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

from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252
from ..const import CONF_CCU_VERSION, CCU_V1, CCU_V2
from .base_webhook_sensor import BaseWebhookSensor

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

    async def handle_update(self, data: dict) -> None:
        """Calculate battery discharge power for CCU V1 and V2."""

        try:
            ccu_version = self._entry.data.get(
                CONF_CCU_VERSION,
                CCU_V1,
            )

            pv_power_raw = data.get("PV_power_total")

            if pv_power_raw is None:
                _LOGGER.debug("BatteryPowerDischarge: PV_power_total fehlt")
                return

            pv_power = float(pv_power_raw)

            if ccu_version == CCU_V2:
                # CCU V2: vorzeichenbehaftete Wechselrichterleistung
                inverter_power_raw = data.get("InverterPowerSigned")

                if inverter_power_raw is None:
                    _LOGGER.debug(
                        "BatteryPowerDischarge: InverterPowerSigned fehlt"
                    )
                    return

                inverter_power = float(inverter_power_raw)

                # Positive Inverterleistung: Einspeisung
                # Negative Inverterleistung: Netzladung
                discharge_power = max(
                    inverter_power - pv_power,
                    0,
                )

            else:
                # CCU V1: bisherige Berechnung
                pccu_raw = data.get("Pccu")

                if pccu_raw is None:
                    _LOGGER.debug("BatteryPowerDischarge: Pccu fehlt")
                    return

                ccu = float(pccu_raw)

                if not is_pccu_ok(ccu):
                    _LOGGER.warning(
                        "BatteryPowerDischarge: Pccu unplausibel: %s W",
                        ccu,
                    )
                    return

                batteries = data.get("batteriesInfo", [])

                if not is_power_total_ok(pv_power, batteries):
                    _LOGGER.warning(
                        "BatteryPowerDischarge: PV-Leistung unplausibel: %s W",
                        pv_power,
                    )
                    return

                discharge_power = max(
                    ccu - pv_power,
                    0,
                )

            self._attr_native_value = round(
                discharge_power,
                2,
            )

            _LOGGER.debug(
                "BatteryPowerDischarge (%s): PV=%s W, Entladung=%s W",
                ccu_version,
                pv_power,
                self._attr_native_value,
            )

        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPowerDischarge: Ungültige Leistungsdaten: %s",
                err,
            )