"""Sensor-Entity zur Darstellung der Batterieleistung für MaxxiChargeConnect.

Dieses Modul definiert die Klasse BatteryPower, eine Home Assistant SensorEntity,
die die aktuelle Batterieleistung basierend auf den eingehenden Webhook-Daten
überwacht und darstellt.

Die Sensor-Entity:
    - Abonniert Webhook-Updates über den Dispatcher.
    - Validiert empfangene Werte mittels externer Hilfsfunktionen.
    - Berechnet die Batterieleistung aus der PV-Leistung und dem CCU-Wert.
    - Aktualisiert den Sensorwert und stellt ihn in Watt dar.

Die Entity ist für die automatische Anzeige in Home Assistant konfiguriert
und besitzt ein eindeutiges Entity-ID-Schema basierend auf dem ConfigEntry.

Abhängigkeiten:
    - homeassistant.components.sensor
    - homeassistant.config_entries
    - homeassistant.helpers.dispatcher
    - custom_components.maxxi_charge_connect.tools (für Validierungshilfen)

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


class BatteryPower(BaseWebhookSensor):
    """Sensor zur Überwachung und Anzeige der Batterieleistung.

    Diese Klasse implementiert eine Home Assistant SensorEntity, die
    Batterieleistung in Watt basierend auf eingehenden Webhook-Daten misst.

    Attributes:
        _entry (ConfigEntry): Der zugehörige ConfigEntry.
        _unsub_dispatcher (callable | None): Funktion zum Abbestellen des Dispatchersignals.

    """

    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "battery_power"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die BatteryPower Sensor-Entität.

        Args:
            entry (ConfigEntry): Der ConfigEntry, der die Konfiguration für diese Instanz enthält.

            Initialisiert die wichtigsten Entity-Attribute wie eindeutige ID, Icon,
            Einheit, Gerätetyp und vorgeschlagene Genauigkeit für die Anzeige.

        """
        super().__init__(entry)
        self._attr_suggested_display_precision = 2
        self._entry = entry
        # self._attr_name = "Battery Power"
        self._attr_unique_id = f"{entry.entry_id}_battery_power"
        self._attr_icon = "mdi:battery-charging-outline"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    async def handle_update(self, data: dict) -> None:
        """Calculate net battery power for CCU V1 and V2."""

        try:
            ccu_version = self._entry.data.get(
                CONF_CCU_VERSION,
                CCU_V1,
            )

            pv_power_raw = data.get("PV_power_total")

            if pv_power_raw is None:
                _LOGGER.debug("BatteryPower: PV_power_total fehlt")
                return

            pv_power = float(pv_power_raw)

            if ccu_version == CCU_V2:
                # CCU V2: vorzeichenbehaftete Wechselrichterleistung
                inverter_power_raw = data.get("InverterPowerSigned")

                if inverter_power_raw is None:
                    _LOGGER.debug(
                        "BatteryPower: InverterPowerSigned fehlt"
                    )
                    return

                inverter_power = float(inverter_power_raw)

                battery_power = pv_power - inverter_power

            else:
                # CCU V1: bisherige Berechnung
                pccu_raw = data.get("Pccu")

                if pccu_raw is None:
                    _LOGGER.debug("BatteryPower: Pccu fehlt")
                    return

                ccu = float(pccu_raw)

                if not is_pccu_ok(ccu):
                    _LOGGER.warning(
                        "BatteryPower: Pccu unplausibel: %s W",
                        ccu,
                    )
                    return

                batteries = data.get("batteriesInfo", [])

                if not is_power_total_ok(pv_power, batteries):
                    _LOGGER.warning(
                        "BatteryPower: PV-Leistung unplausibel: %s W",
                        pv_power,
                    )
                    return

                battery_power = pv_power - ccu

            self._attr_native_value = round(
                battery_power,
                2,
            )

            _LOGGER.debug(
                "BatteryPower (%s): PV=%s W, Netto=%s W",
                ccu_version,
                pv_power,
                self._attr_native_value,
            )

        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "BatteryPower: Ungültige Leistungsdaten: %s",
                err,
            )