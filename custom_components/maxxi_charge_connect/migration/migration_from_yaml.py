import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

_LOGGER = logging.getLogger(__name__)


DEVICE_ID = "deviceid"


class MigrateFromYaml:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry
        self._sensor_map = {}
        self._current_sensors = None

    def load_current_sensors(self):
        """Lädt aktuelle Entitäten zum Gerät aus der HA - Registry"""

        entity_registry = async_get_entity_registry(self._hass)
        neu_sensor_map = {}

        for entity in entity_registry.entities.values():
            if (
                entity.config_entry_id == self._entry.entry_id
                and entity.domain == "sensor"
            ):
                type = entity.unique_id.removeprefix(f"{self._entry.entry_id}_").lower()
                old_type = self.get_type(type)
                neu_sensor_map[entity.entity_id] = (type, old_type, entity)

        return neu_sensor_map

    def get_type(self, value):
        """Liefert den Sensor-Type.

        Es wird aus dem übergebenen String ermittelt, ob der Sensor-Typ einen alten Typ
        von Joern-R beinhaltet"""

        type = value.lower()

        if "battery_power_discharge" in type:  #
            return "batterie_entladen"

        if "battery_soe" in type:  #
            return "ladestand_detail"

        if "battery_power_charge" in type:  #
            return "batterie_laden"

        if "battery_soc" in type:  #
            return "ladestand"

        if "battery_power" in type:  #
            return "batterie_leistung"

        if "ccu_power" in type:  #
            return "ccu_leistung"

        if "firmware_version" in type:  #
            return "ccu_version"

        if "deviceid" in type:  #
            return "deviceid"

        if "rssi" in type:
            return "wifi_signalstarke_dbm"  #

        if "pv_power" in type:  #
            return "pv_leistung"

        if "power_meter" in type:  #
            return "e_zaehler_leistungswert"

        if "grid_import" in type:
            return "e_zaehler_netzbezug"

        if "grid_export" in type:
            return "e_zaehler_netzeinspeisung"

        if "batterytotalenergycharge" in type:
            return "batterie_laden_kwh"

        if "batterytotalenergydischarge" in type:
            return "batterie_entladen_kwh"

        if "gridimportenergytotal" in type:
            return "e_zaehler_netzbezug_kwh"

        if "gridexportenergytotal" in type:
            return "e_zaehler_netzeinspeisung_kwh"

        if "pvtotalenergy" in type:
            return "pv_leistung_kwh"

        return None

    def get_new_sensor(self, old_entity_id):
        """Ermittelt den neuen Sensor, der dem alten Sensor entspricht"""
        if old_entity_id is None or self._current_sensors is None:
            return None

        for entity_id, (sensor_type, old_type, entity) in self._current_sensors.items():
            if old_type is not None and old_type in old_entity_id:
                return entity_id

        return None

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
        # name = (state.name or "").lower()
        name = (state.friendly_name or "").lower()
        # name = state.attributes.get("friendly_name", state.entity_id).lower()

        # unit = state.attributes.get("unit_of_measurement", "").lower()
        # device_class = state.attributes.get("device_class", "").lower()

        # name = state

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
        if "deviceid" in name:
            return "DeviceId"

        return None

    async def async_notify_possible_migration(self):
        old_sensors = self.find_old_maxxicharge_sensors()

        if not old_sensors:
            _LOGGER.info("Keine alten Sensoren zur Migration erkannt.")
            return

        self._current_sensors = self.load_current_sensors()

        lines = ["Folgende alte Sensoren wurden erkannt:\n"]

        for eid in old_sensors:
            lines.append(f'- old_sensor: "{eid}"')

            new_entity_id = self.get_new_sensor(eid)
            if new_entity_id is None:
                lines.append(f'  new_sensor: "sensor.HIER_EINTRAGEN"')
            else:
                lines.append(f'  new_sensor: "{new_entity_id}"')

        sensor_block = "\n".join(lines)

        message = (
            "Die folgenden alten MaxxiCharge-Sensoren wurden erkannt und könnten migriert werden.\n\n"
            "Kopiere den folgenden Block und verwende ihn im Service `maxxi_charge_connect.migration_von_yaml_konfiguration`:\n\n"
            "```yaml\n"
            f"{sensor_block}"
            "\n```"
        )

        await self._hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "MaxxiCharge Migration möglich",
                "message": message,
                "notification_id": "maxxicharge_migration_hint",
            },
        )

    async def async_handle_trigger_migration(
        self, sensor_mapping: list[dict] | None = None
    ):
        _LOGGER.info("Starte Migration ...")

        entity_registry = async_get_entity_registry(self._hass)
        self._current_sensors = self.load_current_sensors()

        if self._current_sensors is None:
            _LOGGER.error(
                "Aktuelle Senoren konnten nicht geladen werden. Migration nicht möglch"
            )
            return

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

            # hole zugehörige Entity aus current_sensors
            sensor_info = self._current_sensors.get(new_entity_id)
            if not sensor_info:
                _LOGGER.warning("Neue Entity %s nicht gefunden", new_entity_id)
                continue

            type, old_type, entity = sensor_info

            if not old_type or not entity:
                _LOGGER.warning(
                    "Sensor-Typ von %s konnte nicht erkannt werden", new_entity_id
                )
                continue

            sensor_map[old_type] = new_entity_id
            _LOGGER.info(
                "Mapping: %s → %s (Typ: %s)", old_entity_id, new_entity_id, type
            )

            # Schritt 1: Temporären Namen erzeugen
            # temp_entity_id = f"{new_entity_id}_to_be_removed"

            # # 1. Neue Entity umbenennen (temporär freimachen)
            # try:
            #     entity_registry.async_update_entity(
            #         entity_id=new_entity_id, new_entity_id=temp_entity_id
            #     )
            #     _LOGGER.info(
            #         "Temporär umbenannt: %s → %s", new_entity_id, temp_entity_id
            #     )
            # except Exception as e:
            #     _LOGGER.warning(
            #         "Konnte %s nicht temporär umbenennen: %s", new_entity_id, e
            #     )

            # await self._hass.async_block_till_done()

            # Alte Entity zur neuen machen

            try:
                if entity:
                    _LOGGER.warning("%s -> %s", new_entity_id, old_entity_id)

                    entity_registry.async_remove(old_entity_id)
                    await self._hass.async_block_till_done()

                    entity_registry.async_update_entity(
                        entity_id=new_entity_id, new_entity_id=old_entity_id
                    )
                else:
                    _LOGGER.error("Neuer Unique-Key konnte nicht gesetzt werden")
                    return
            except Exception as e:
                _LOGGER.error("Fehler beim Umbenennen der Entity: %s", e)

            # ConfigEntry aktualisieren
            self._hass.config_entries.async_update_entry(
                self._entry,
                data={
                    **self._entry.data,
                    "migration": True,
                    "legacy_sensor_map": sensor_map,
                },
            )

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

        await self._hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "MaxxiCharge Migration",
                "message": f"Migration für {len(sensor_mapping)} Sensoren wurde durchgeführt.",
            },
        )

        _LOGGER.info("Migration abgeschlossen.")
