"""Battery SOC Sensor für MaxxiChargeConnect.

Dieses Modul definiert die BatterySoc-Sensor-Entity, die den Ladezustand (State of Charge, SOC)
der Batterie in Prozent darstellt. Der Sensor empfängt die Werte über einen Dispatcher,
der durch Webhook-Daten aktualisiert wird.

Der Sensor wird dynamisch in Home Assistant registriert und aktualisiert.
"""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE

from .base_webhook_sensor import BaseWebhookSensor

from ..const import (
    DOMAIN,
    CONF_WINTER_MODE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MAX_CHARGE,
)

from ..tools import (
    async_get_min_soc_entity
)

_LOGGER = logging.getLogger(__name__)

# Konstanten für Wintermodus-Steuerung
WINTER_MODE_CHANGE_DELAY = 5  # Sekunden Verzögerung bei Grenzwert-Änderungen


class BatterySoc(BaseWebhookSensor):
    """SensorEntity zur Darstellung des Ladezustands (SOC) einer Batterie in Prozent.

    Der Sensor verwendet Dispatcher-Signale, um sich automatisch zu aktualisieren,
    sobald neue Daten über den konfigurierten Webhook empfangen werden.
    """

    _attr_translation_key = "BatterySoc"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den BatterySoc-Sensor.

        Args:
            entry (ConfigEntry): Die Konfigurationsdaten aus dem Home Assistant ConfigEntry.

        """
        super().__init__(entry)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_battery_soc"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._remove_listener = None

    async def _check_upper_limit_reached(self, cur_value: float, cur_min_limit: float) -> bool:
        """Überprüft, ob der SOC den oberen Grenzwert im Wintermodus erreicht hat.

        Args:
            cur_value: Aktueller SOC-Wert
            cur_min_limit: Aktuelle minSOC-Einstellung

        Returns:
            bool: True, wenn der SOC den oberen Grenzwert erreicht oder überschritten hat, sonst False.
        """
        winter_min_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MIN_CHARGE, 20))
        winter_max_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MAX_CHARGE, 60))

        _LOGGER.debug(
            "Wintermodus - Upper Limit Check: cur_value=%s, cur_min_limit=%s, winter_min=%s, winter_max=%s",
            cur_value, cur_min_limit, winter_min_charge, winter_max_charge
        )

        return cur_value >= winter_max_charge and cur_min_limit != winter_min_charge

    async def _check_lower_limit_reached(self, cur_value: float, cur_min_limit: float) -> bool:
        """Überprüft, ob der SOC den unteren Grenzwert im Wintermodus erreicht hat.

        Args:
            cur_value: Aktueller SOC-Wert
            cur_min_limit: Aktuelle minSOC-Einstellung

        Returns:
            bool: True, wenn der SOC den unteren Grenzwert erreicht oder unterschritten hat, sonst False.
        """
        winter_min_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MIN_CHARGE, 20))
        winter_max_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MAX_CHARGE, 60))

        _LOGGER.debug(
            "Wintermodus - Lower Limit Check: cur_value=%s, cur_min_limit=%s, winter_min=%s, winter_max=%s",
            cur_value, cur_min_limit, winter_min_charge, winter_max_charge
        )

        return cur_value <= winter_min_charge and cur_min_limit != winter_max_charge

    async def _do_wintermode(self, native_value: float):
        """Führt Wintermodus-Logik aus und passt minSOC bei Bedarf an.

        Args:
            native_value: Aktueller SOC-Wert
        """
        winter_min_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MIN_CHARGE, 20))
        winter_max_charge = float(self.hass.data[DOMAIN].get(CONF_WINTER_MAX_CHARGE, 60))

        _LOGGER.debug(
            "Wintermodus aktiv - SOC=%s, winter_min=%s, winter_max=%s",
            native_value, winter_min_charge, winter_max_charge
        )

        try:
            min_soc_entity, cur_state = await async_get_min_soc_entity(self.hass, self._entry.entry_id)

            if min_soc_entity is None or cur_state is None:
                _LOGGER.warning("Wintermodus: min_soc_entity oder cur_state nicht verfügbar")
                return

            cur_state_float = float(cur_state.state)

            if await self._check_lower_limit_reached(native_value, cur_state_float):
                _LOGGER.debug("Setze minSoc auf WinterMaxCharge: %s", winter_max_charge)
                await min_soc_entity.set_change_limitation(winter_max_charge, WINTER_MODE_CHANGE_DELAY)

            elif await self._check_upper_limit_reached(native_value, cur_state_float):
                _LOGGER.debug("Setze minSoc auf WinterMinCharge: %s", winter_min_charge)
                await min_soc_entity.set_change_limitation(winter_min_charge, WINTER_MODE_CHANGE_DELAY)

            else:
                _LOGGER.debug("Keine Anpassung des min_soc erforderlich.")

        except Exception as err:
            _LOGGER.error("Fehler bei Wintermodus-Steuerung: %s", err)

    async def handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen Daten, erwartet ein 'SOC'-Feld mit dem Prozentwert.

        """
        try:
            soc_raw = data.get("SOC")
            if soc_raw is None:
                _LOGGER.warning("SOC-Daten im Webhook fehlen")
                self._attr_available = False
                return

            native_value_float = float(str(soc_raw).strip())
            
            # Plausibilitätsprüfung: SOC sollte zwischen 0 und 100% liegen
            if not (0 <= native_value_float <= 100):
                _LOGGER.warning("Unplausible SOC: %s%% (erwartet 0-100%%)", native_value_float)
                self._attr_available = False
                return

            self._attr_available = True
            self._attr_native_value = native_value_float
            
        except (ValueError, TypeError) as err:
            _LOGGER.error("Ungültiger SOC-Wert empfangen: %r, Fehler: %s", soc_raw, err)
            self._attr_available = False
            return

        wintermode = self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False)
        _LOGGER.debug(
            "BatterySoc Update: SOC=%s%%, Wintermode=%s, updating state.",
            self._attr_native_value, wintermode
        )

        if wintermode:
            await self._do_wintermode(native_value_float)
        else:
            _LOGGER.debug("Normalmodus - UI wird aktualisiert")

        self.async_write_ha_state()

    @property
    def icon(self):
        """Return dynamic battery icon based on SOC percentage."""
        if self._attr_native_value is None:
            return "mdi:battery-unknown"

        try:
            level = max(0, min(100, int(self._attr_native_value)))  # Clamping 0–100
            level = round(level / 10) * 10  # z. B. 57 → 60

        except (TypeError, ValueError):
            return "mdi:battery-unknown"
        else:
            if level == 100:
                return "mdi:battery"
            elif level == 0:
                return "mdi:battery-outline"
            else:
                return f"mdi:battery-{level}"
