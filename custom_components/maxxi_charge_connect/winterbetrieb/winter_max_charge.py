import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.helpers.event import async_track_state_change_event, async_call_later

from ..http_post.number_config_entity import (
    NumberConfigEntity,
) 

# from homeassistant.core import Event
# from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    DEVICE_INFO,
    DOMAIN,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class WinterMaxCharge(NumberEntity):
    """NumberEntity für die Anzeige der minimalen Entladeleistung im Winterbetrieb."""

    _attr_translation_key = "winter_max_charge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_winter_max_charge"
        
        # self._attr_icon = "mdi:identifier"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = PERCENTAGE
        self.attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self.set_value(60)
        
#    async def async_update(self):        
 #       self._attr_available = False
        

        
    
        

    #        self._attr_extra_state_attributes = {"reason": "Winterbetrieb deaktiviert"}

    # self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    # async def async_added_to_hass(self):

    # if self._enable_cloud_data:
    #     _LOGGER.info("Daten kommen vom Proxy")
    #     self.hass.bus.async_listen(
    #         PROXY_STATUS_EVENTNAME, self.async_update_from_event
    #     )
    # else:
    #     _LOGGER.info("Daten kommen vom Webhook")

    #     signal_sensor = (
    #         f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"
    #     )

    #     self.async_on_remove(
    #         async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
    #     )

    # async def async_update_from_event(self, event: Event):
    # """Aktualisiert Sensor von Proxy-Event."""

    # json_data = event.data.get("payload", {})

    # if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
    #     await self._handle_update(json_data)

    # async def _handle_update(self, data):
    #     """Verarbeitet eingehende Webhook-Daten und aktualisiert die Geräte-ID.

    #     Args:
    #         data (dict): Die per Webhook empfangenen Daten.

    #     """

    #     self._attr_native_value = data.get("deviceId")
    #     self.async_write_ha_state()

    def set_value(self, value):
        """SetValue."""
        self._attr_native_value = value

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese  Entity.

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
