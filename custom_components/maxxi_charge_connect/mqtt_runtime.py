"""Home Assistant ownership of the shared internal MQTT broker."""

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .const import DOMAIN, MQTT_BROKER_MANAGER
from .mqtt_broker_manager import MqttBrokerManager


def get_broker_manager(hass: HomeAssistant) -> MqttBrokerManager:
    """Create once without yielding, including when entries set up concurrently."""
    data = hass.data.setdefault(DOMAIN, {})
    if MQTT_BROKER_MANAGER not in data:
        manager = data[MQTT_BROKER_MANAGER] = MqttBrokerManager()

        async def stop_broker(event):
            await manager.async_shutdown()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_broker)
    return data[MQTT_BROKER_MANAGER]
