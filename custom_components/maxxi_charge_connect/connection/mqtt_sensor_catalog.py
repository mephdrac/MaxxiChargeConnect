"""Explicit provenance for every sensor created by the CCU V2 factories."""

from ..const import DOMAIN, MQTT_DISCOVERY_COORDINATOR

DERIVED_SOURCES = {
    "battery_power_charge": ("pv_power", "ccu_power"),
    "battery_power_discharge": ("pv_power", "ccu_power"),
    "battery_power": ("battery_power_charge", "battery_power_discharge"),
    "grid_import": ("power_meter",),
    "grid_export": ("power_meter",),
    "power_consumption": ("power_meter", "ccu_power"),
    "pv_consumption": ("pv_power", "power_meter"),
}

LOCAL_SENSORS = {
    "mqtt_last_received",
    "mqtt_received_count",
    "mqtt_discovered_entities",
    "mqtt_sensor_coverage",
}


def register_sensors(hass, entry, entities, *, dependencies=None):
    """Register actual factory output, including disabled and dynamic entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id].get(MQTT_DISCOVERY_COORDINATOR)
    if coordinator is not None:
        coordinator.register_existing_sensors(entities, dependencies=dependencies)
