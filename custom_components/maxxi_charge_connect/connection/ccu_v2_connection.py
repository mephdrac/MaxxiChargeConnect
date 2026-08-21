import json
import logging

from homeassistant.components import mqtt
from homeassistant.const import Platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


from .ccu_base_connection import CcuBaseConnection
from ..const import (
    DOMAIN,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
    CONF_DEVICE_ID
)

_LOGGER = logging.getLogger(__name__)


class ccuV2Connection(CcuBaseConnection):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
            super().__init__(hass, entry)
            self.base_topic = self.entry.data.get(CONF_DEVICE_ID)

    async def async_setup(self) -> None:        
        raise NotImplementedError

    async def async_setup_entry(self) -> bool:

        _LOGGER.warning(self.base_topic)

        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN].setdefault(self.entry.entry_id, {})

        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        entry_data["v2_state"] = {}

        entry_data[WEBHOOK_SIGNAL_UPDATE] = (
            f"{DOMAIN}_{self.entry.entry_id}_update"
        )

        entry_data[WEBHOOK_SIGNAL_STATE] = (
            f"{DOMAIN}_{self.entry.entry_id}_state"
        )

        subscriptions = {
            "powermeter/telemetry": self._parse_powermeter,
            "battery/telemetry": self._parse_battery,
        }

        entry_data["mqtt_unsubscribers"] = []

        for topic_suffix, parser in subscriptions.items():
            unsubscribe = await mqtt.async_subscribe(
                self.hass,
                f"{self.base_topic}/{topic_suffix}",
                self._create_message_handler(entry_data, parser),
                qos=0,
            )

            entry_data["mqtt_unsubscribers"].append(unsubscribe)

        await self.hass.config_entries.async_forward_entry_setups(
            self.entry,
            [Platform.SENSOR],
        )

        return True

    def _parse_powermeter(self, data: dict) -> dict:
        power = data.get("power")

        if power is None:
            return {}

        return {
            "Pr": power,
        }

    def _parse_battery(self, data: dict) -> dict:
        batteries = data.get("batteries", [])

        soc_values = [
            battery["soc"]
            for battery in batteries
            if battery.get("soc") is not None
        ]

        if not soc_values:
            return {}

        return {
            "SOC": sum(soc_values) / len(soc_values),
        }

    def _create_message_handler(self, entry_data, parser):
        async def message_received(msg):
            try:
                data = json.loads(msg.payload)

                values = parser(data)

                if not values:
                    return

                entry_data["v2_state"].update(values)

                async_dispatcher_send(
                    self.hass,
                    entry_data[WEBHOOK_SIGNAL_UPDATE],
                    entry_data["v2_state"],
                )

            except (json.JSONDecodeError, TypeError, ValueError) as err:
                _LOGGER.warning(
                    "Ungültige MQTT-Daten auf %s: %s",
                    msg.topic,
                    err,
                )

        return message_received

    async def async_unload(self) -> None:
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]

        for unsubscribe in entry_data.get("mqtt_unsubscribers", []):
            unsubscribe()