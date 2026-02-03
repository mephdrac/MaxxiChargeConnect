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
from .base_webhook_sensor import BaseWebhookSensor

from ..tools import is_pccu_ok, is_power_total_ok  # noqa: TID252

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

    async def handle_update(self, data):
        """Verarbeitet empfangene Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen JSON-Daten vom Webhook.

        Validiert die eingehenden Werte mit Hilfsfunktionen und berechnet
        die Batterieleistung. Aktualisiert dann den Sensorstatus.

        """
        try:
            # CCU-Verbrauch sicher abfragen
            pccu_raw = data.get("Pccu")
            if pccu_raw is None:
                _LOGGER.debug("BatteryPower: Pccu fehlt")
                return

            ccu = float(pccu_raw)

            if not is_pccu_ok(ccu):
                _LOGGER.warning("BatteryPower: PCCU-Wert nicht plausibel: %s W", ccu)
                return

            # PV-Leistung sicher abfragen
            pv_power_raw = data.get("PV_power_total")
            if pv_power_raw is None:
                _LOGGER.debug("BatteryPower: PV_power_total fehlt")
                return

            pv_power = float(pv_power_raw)
            batteries = data.get("batteriesInfo", [])

            if not is_power_total_ok(pv_power, batteries):
                _LOGGER.warning(
                    "BatteryPower: PV-Leistung nicht plausibel: %s W", pv_power
                )
                return

            # Netto-Batterieleistung berechnen (kann positiv oder negativ sein)
            battery_power = round(pv_power - ccu, 3)

            self._attr_native_value = battery_power
            _LOGGER.debug(
                "BatteryPower: Netto-Batterieleistung berechnet: %s W (PV: %s W, CCU: %s W)",
                battery_power,
                pv_power,
                ccu,
            )

        except (ValueError, TypeError) as err:
            _LOGGER.warning("BatteryPower: Konvertierungsfehler: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("BatteryPower: Unerwarteter Fehler: %s", err)
