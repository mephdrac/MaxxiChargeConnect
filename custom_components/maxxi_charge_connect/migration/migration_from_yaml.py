import logging
from homeassistant.core import HomeAssistant, ServiceCall
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

    async def async_handle_trigger_migration(self, sensor_mapping: list[dict]):
        _LOGGER.info("Starte Migration ...")

        # Sensors aus Service-Aufruf holen (kann leer sein)

        _LOGGER.warning("Starte Migration für Sensoren: %s", sensor_mapping)

        # Mapping aus Typ → neue Entity-ID
        sensor_map = {}
        # Hole alle States nur einmal
        all_states = {s.entity_id: s for s in self._hass.states.async_all()}

        for mapping in sensor_mapping:
            old_entity_id = mapping.get("old_sensor")
            new_entity_id = mapping.get("new_sensor")

            if not old_entity_id or not new_entity_id:
                _LOGGER.warning("Ungültiges Mapping übersprungen: %s", mapping)
                continue

            old_state = all_states.get(old_entity_id)
            if not old_state:
                _LOGGER.warning("Alter Sensor %s nicht gefunden", old_entity_id)
                continue

            sensor_type = self.detect_sensor_type(old_state)
            if not sensor_type:
                _LOGGER.warning(
                    "Sensor-Typ von %s konnte nicht erkannt werden", old_entity_id
                )
                continue

            sensor_map[sensor_type] = new_entity_id
            _LOGGER.info(
                "Mapping: %s → %s (Typ: %s)", old_entity_id, new_entity_id, sensor_type
            )

            if not sensor_map:
                _LOGGER.warning("Keine gültigen Mappings gefunden. Abbruch")
            return

        # _LOGGER.warning("AllStates: %s", all_states)

        # for cur_mappping in sensor_mapping:
        #     _LOGGER.warning("Sensor-Map: %s", cur_mappping)

        # if sensor_ids:
        #     _LOGGER.info(f"Verwende übergebene Sensoren: {sensor_ids}")
        #     # all_states = {s.entity_id: s for s in self._hass.states.async_all()}
        #     # sensors = {eid: all_states[eid] for eid in sensor_ids if eid in all_states}
        # else:
        #     _LOGGER.info("Erkenne Sensoren automatisch ...")
        # sensors = self.find_old_maxxicharge_sensors()

        # _LOGGER.info("Gefundene Sensoren zur Migration: %s", list(sensors.keys()))

        # Mapping aus Typ → Entity-ID erzeugen
        # sensor_map = {}
        # for entity_id, state in sensors.items():
        #     sensor_type = self.detect_sensor_type(state)
        #     if sensor_type and sensor_type not in sensor_map:
        #         sensor_map[sensor_type] = entity_id

        # ConfigEntry aktualisieren
        # self._hass.config_entries.async_update_entry(
        #     self._entry,
        #     data={
        #         **self._entry.data,
        #         "migration": True,
        #         "legacy_sensor_map": sensor_map,
        #     },
        # )

        # await self._hass.services.async_call(
        #     "persistent_notification",
        #     "create",
        #     {
        #         "title": "MaxxiCharge Migration",
        #         "message": f"Migration für {len(sensor_mapping)} Sensoren wurde durchgeführt.",
        #     },
        # )

        _LOGGER.info("Migration abgeschlossen.")
