"""Battery SOC Sensor für MaxxiChargeConnect.

Dieses Modul definiert die BatterySoc-Sensor-Entity, die den Ladezustand (State of Charge, SOC)
der Batterie in Prozent darstellt. Der Sensor empfängt die Werte über einen Dispatcher,
der durch Webhook-Daten aktualisiert wird.

Der Sensor wird dynamisch in Home Assistant registriert und aktualisiert.
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, PERCENTAGE
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252


class BatterySoc(SensorEntity):
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

        self._unsub_dispatcher = None
        self._entry = entry
        # self._attr_name = "Battery SOC"
        self._attr_unique_id = f"{entry.entry_id}_battery_soc"
        self._attr_native_value = None
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    async def async_added_to_hass(self):
        """Registriert den Sensor beim Dispatcher, wenn die Entity Home Assistant hinzugefügt wird.

        Dadurch wird sichergestellt, dass der Sensor automatisch aktualisiert wird,
        sobald neue Daten über den zugehörigen Webhook eintreffen.
        """

        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        """Hebt die Registrierung des Dispatchers auf, wenn der Sensor entfernt wird."""
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Verarbeitet eingehende Webhook-Daten und aktualisiert den Sensorwert.

        Args:
            data (dict): Die empfangenen Daten, erwartet ein 'SOC'-Feld mit dem Prozentwert.

        """
        self._attr_native_value = data.get("SOC", 0)
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return dynamic battery icon based on SOC percentage."""
        result = "mdi:battery-unknown"

        try:
            level = max(0, min(100, int(self._attr_native_value)))  # Clamping 0–100
            level = round(level / 10) * 10  # z. B. 57 → 60            
            
        except (TypeError, ValueError):
            result = "mdi:battery-unknown"
        else:
            result = f"mdi:battery-{level}"
                    
        return result

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
