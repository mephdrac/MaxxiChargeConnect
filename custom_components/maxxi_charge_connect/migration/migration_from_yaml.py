import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class MigrateFromYaml:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry

    def find_old_maxxicharge_sensors(self):
        sensors = {}
        for state in self._hass.states.async_all("sensor"):
            if (
                "maxxi" in state.entity_id.lower()
                or "maxxi" in (state.name or "").lower()
            ):
                sensors[state.entity_id] = state
        return sensors

    def detect_sensor_type(self, state):
        name = (state.name or "").lower()
        unit = state.attributes.get("unit_of_measurement", "").lower()
        device_class = state.attributes.get("device_class", "").lower()

        if "ladestand %" in name or (unit == "%" and "battery" in name):
            return "soc"
        if "ladestand detail" in name or unit == "wh":
            return "capacity_wh"
        if "leistung" in name and "ccu" in name:
            return "ccu_power"
        if "leistung" in name and "batterie" in name:
            return "battery_power"
        if "signalstärke" in name or device_class == "signal_strength":
            return "wifi_signal_strength"
        if "firmware" in name:
            return "firmware_version"
        return None

    def async_handle_trigger_migration(self, call):
        _LOGGER.warning("Starte die Migration ...")
        old_sensors = self.find_old_maxxicharge_sensors()
        sensor_map = {}
        for entity_id, state in old_sensors.items():
            sensor_type = self.detect_sensor_type(state)
            if sensor_type and sensor_type not in sensor_map:
                sensor_map[sensor_type] = entity_id

        # # Update ConfigEntry mit Migrationsdaten
        # self._hass.config_entries.async_update_entry(
        #     self._entry,
        #     data={
        #         **self._entry.data,
        #         "migration": True,
        #         "legacy_sensor_map": sensor_map,
        #     },
        # )

        # # Optional: Notification für User
        # self._hass.components.persistent_notification.async_create(
        #     "Migration der alten MaxxiCharge YAML-Sensoren wurde ausgeführt.",
        #     title="MaxxiCharge Migration",
        # )
        _LOGGER.warning("Migration beendet")
