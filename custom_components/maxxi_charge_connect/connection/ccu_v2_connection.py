import json
import logging
import json

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.components import mqtt
from homeassistant.const import Platform

from .ccu_base_connection import CcuBaseConnection

from ..const import (
    DOMAIN,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


class ccuV2Connection(CcuBaseConnection):

    async def async_setup(self) -> None:
        raise NotImplementedError

    async def async_setup_entry(self) -> bool:
        """Initialisiert CCU V2 über MQTT."""

        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN].setdefault(self.entry.entry_id, {})


        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]

        entry_data[WEBHOOK_SIGNAL_UPDATE] = (
            f"{DOMAIN}_{self.entry.entry_id}_update"
        )

        entry_data[WEBHOOK_SIGNAL_STATE] = (
            f"{DOMAIN}_{self.entry.entry_id}_state"
        )

        topic = "???/powermeter/telemetry"

        async def message_received(msg):
            data = json.loads(msg.payload)

            power = data.get("power")

            normalized_data = {
                "Pr": power,
            }

            async_dispatcher_send(
                self.hass,
                entry_data[WEBHOOK_SIGNAL_UPDATE],
                normalized_data,
            )

        unsubscribe = await mqtt.async_subscribe(
            self.hass,
            topic,
            message_received,
            qos=0,
        )

        entry_data["mqtt_unsubscribe"] = unsubscribe


        await self.hass.config_entries.async_forward_entry_setups(
            self.entry,
            [Platform.SENSOR],
        )

        return True

    async def async_unload(self) -> None:
        unsubscribe = self.hass.data[DOMAIN][self.entry.entry_id].get(
            "mqtt_unsubscribe"
        )

        if unsubscribe:
            unsubscribe()