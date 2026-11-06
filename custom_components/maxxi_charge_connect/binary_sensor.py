"""CCU V2 binary sensors announced through MQTT discovery."""

from .devices.mqtt_discovery_entity import setup_discovery_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_discovery_entities(hass, entry, async_add_entities, "binary_sensor")
