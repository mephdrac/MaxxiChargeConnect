"""Set up CCU V2 binary sensors announced through MQTT discovery.

Entity creation is delegated to the shared discovery setup helper, using
the binary_sensor platform to expose states with two possible values.
"""

from .devices.mqtt_discovery_entity import setup_discovery_entities


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MQTT discovery binary sensors for a config entry.

    Args:
        hass: Home Assistant instance managing the integration.
        entry: Config entry for which binary sensor entities are registered.
        async_add_entities: Callback used to add entities to the binary
            sensor platform.
    """
    # Delegate entity setup to the shared helper for the binary_sensor platform.
    setup_discovery_entities(hass, entry, async_add_entities, "binary_sensor")
