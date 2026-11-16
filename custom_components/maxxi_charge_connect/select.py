"""Set up CCU V2 select entities announced through MQTT discovery.

Entity creation is delegated to the shared discovery setup helper, using
the select platform to expose settings with a predefined list of options.
"""

from .devices.mqtt_discovery_entity import setup_discovery_entities


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MQTT discovery select entities for a config entry.

    Args:
        hass: Home Assistant instance managing the integration.
        entry: Config entry for which select entities are registered.
        async_add_entities: Callback used to add entities to the select
            platform.
    """
    # Delegate entity setup to the shared helper for the select platform.
    setup_discovery_entities(hass, entry, async_add_entities, "select")
