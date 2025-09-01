"""Modul für die BatterySoESensor-Entität der maxxi_charge_connect Integration.

Definiert eine Sensor-Entität, einer einzelnen Batterie darstellt,
dynamische Aktualisierungen verarbeitet
und Geräteinformationen für Home Assistant bereitstellt.
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252


class BatteryMpptAmpereSensor(SensorEntity):
    """Sensor-Entität zur Darstellung der Stromstärke einer bestimmten Batterie.

    Attribute:
        _entry (ConfigEntry): Konfigurationseintrag für diese Sensor-Instanz.
        _index (int): Index der Batterie, die dieser Sensor repräsentiert.

    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "BatteryMpptAmpereSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, index: int) -> None:
        """Initialisiert die BatteryMpptAmpereSensor-Entität.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.
            index (int): Index der Batterie, für die der Sensor steht.

        """
        self._entry = entry
        self._index = index
        self._attr_translation_placeholders = {"index": str(index + 1)}
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = f"{entry.entry_id}_battery_mppt_ampere_sensor_{index}"
        self._attr_icon = "mdi:alpha-a-circle"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Registriert den Update-Handler dieses Sensors beim Dispatcher.

        Wird aufgerufen, wenn die Entität in Home Assistant hinzugefügt wird.
        """
        self.hass.data[DOMAIN][self._entry.entry_id]["listeners"].append(
            self._handle_update
        )

    async def _handle_update(self, data):
        """Verarbeitet eine Aktualisierung und aktualisiert den Sensorwert.

        Args:
            data (dict): Die eingehenden Aktualisierungsdaten mit Batterieinformationen.

        Hinweis:
            Ignoriert IndexError und KeyError stillschweigend, falls die Batterieinformationen
            nicht vorhanden oder fehlerhaft sind.

        """
        try:
            self._attr_native_value = float(data["batteriesInfo"][self._index][
                "mpptCurrent"
            ]) / 1000.0
            self.async_write_ha_state()
        except (IndexError, KeyError):
            pass

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
