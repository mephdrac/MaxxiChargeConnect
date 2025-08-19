import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from ..const import (
    DOMAIN,
    PROXY_ERROR_EVENTNAME,
    DEVICE_INFO,
    PROXY_ERROR_DEVICE_ID,
    CONF_DEVICE_ID,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)

# SENSOR_TYPES = {
#     PROXY_ERROR_DEVICE_ID: "Geräte-ID",
#     "ccu": "CCU",
#     "ip": "IP-Adresse",
#     "error_code": "Fehlercode",
#     "error_message": "Fehlermeldung",
#     "total_errors": "Gesamtanzahl Fehler",
#     "last_payload": "Letzter Payload",
#     "forwarding": "Cloud-Forwarding Status",
#     "uptime": "Uptime"
# }


class ProxySensor(SensorEntity):
    """Sensor für MaxxiCloud-Daten vom Proxy."""

    def __init__(self, entry: ConfigEntry):
        self._entry = entry
        # self._key = key

        self._attr_name = "MeinTestsensor"
        self._attr_unique_id = f"{entry.entry_id}_proxy_sensor"

        self._state = None
        self._attr_native_value = None
        self._attr_device_class = None
        self._attr_icon = "mdi:home-battery"

        self._attr_extra_state_attributes = {}
        # _LOGGER.warning("SENSOR - INITIALISIERT: %s", name)

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        """Register.

        Registriert den Sensor für Updates über das Dispatcher-Signal
        bei Hinzufügen zur Home Assistant Instanz.
        """
        _LOGGER.info("Listen to Event")
        self.hass.bus.async_listen(PROXY_ERROR_EVENTNAME, self.async_update_from_event)

    def format_uptime(self, seconds: int):
        days, remainder = divmod(seconds, 86400)  # 86400 Sekunden pro Tag
        hours, remainder = divmod(remainder, 3600)  # 3600 Sekunden pro Stunde
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attr_extra_state_attributes

    def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        _LOGGER.debug("Event erhalten: %s", self._attr_name)

        data = event.data
        json_data = data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            data = event.data
            self._state = "OK"
            # json_data = data.get("payload", {})
            self._attr_extra_state_attributes = data.get("payload", {})
        # self._state = "TEST"

        # if self._key == PROXY_ERROR_DEVICE_ID:
        #     self._state = data.get(PROXY_ERROR_DEVICE_ID)
        # elif self._key == "ccu":
        #     self._state = data.get("ccu")
        # elif self._key == "uptime":
        #     uptime_seconds = int(json_data.get("uptime"))
        #     self._state = self.format_uptime(uptime_seconds)

        # elif self._key == "ip":
        #     self._state = data.get("ip")
        # elif self._key == "error_code":
        #     self._state = data.get("error_code")
        # elif self._key == "error_message":
        #     self._state = data.get("error_message")
        # elif self._key == "total_errors":
        #     self._state = data.get("total_errors")
        # elif self._key == "last_payload":
        #     self._state = str(data.get("payload", {}))[:100]
        # elif self._key == "forwarding":
        #     self._state = "enabled" if data.get("forwarded") else "disabled"

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
