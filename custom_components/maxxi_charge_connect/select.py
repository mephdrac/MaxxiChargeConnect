"""CCU V2 select settings announced through MQTT discovery."""

from .devices.mqtt_discovery_entity import setup_discovery_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_discovery_entities(hass, entry, async_add_entities, "select")
