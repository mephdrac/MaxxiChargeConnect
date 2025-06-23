import sqlite3
import os

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from homeassistant.components.recorder.statistics import clear_statistics

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
                typ = entity.unique_id.removeprefix(f"{self._entry.entry_id}_").lower()
                old_typ = self.get_type(typ)
                neu_sensor_map[entity.entity_id] = (typ, old_typ, entity)

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

        if "battery_state_of_energy" in type:
            return "pv_leistung_kwh"

        return None

    def get_new_sensor(self, old_entity):
        """Ermittelt den neuen Sensor, der dem alten Sensor entspricht"""
        if old_entity is None or self._current_sensors is None:
            return None

        for entity_id, (sensor_type, old_type, entity) in self._current_sensors.items():
            if sensor_type is not None and sensor_type == self.get_type_from_unique_id(
                old_entity.unique_id
            ):
                return entity_id

        return None

    def get_type_from_unique_id(self, unique_id):
        typ = unique_id.lower()

        if typ.endswith("batterie_entladen"):
            return "battery_power_discharge"

        if typ.endswith("ladestand_detail"):
            return "battery_soe"

        if typ.endswith("batterie_laden"):
            return "battery_power_charge"

        if typ.endswith("ladestand"):
            return "battery_soc"

        if typ.endswith("batterie_leistung"):
            return "battery_power"

        if typ.endswith("ccu_gesamtleistung"):
            return "ccu_power"

        if typ.endswith("ccu_version"):
            return "firmware_version"

        if typ.endswith("deviceid"):
            return "deviceid"

        if typ.endswith("wifi-dbm"):
            return "rssi"  #

        if typ.endswith("pv_leistung"):
            return "pv_power"

        if typ.endswith("e-leistung"):
            return "power_meter"

        if typ.endswith("e_zaehler_netzbezug"):
            return "grid_import"

        if typ.endswith("e_zaehler_netzeinspeisung"):
            return "grid_export"

        if typ.endswith("batterie_laden_kwh"):
            return "batterytotalenergycharge"

        if typ.endswith("batterie_entladen_kwh"):
            return "batterytotalenergydischarge"

        if typ.endswith("e_zaehler_netzbezug_kwh"):
            return "gridimportenergytotal"

        if typ.endswith("e_zaehler_netzeinspeisung_kwh"):
            return "gridexportenergytotal"

        if typ.endswith("pv_leistung_kwh"):
            return "pvtotalenergy"

        if typ.endswith("ladestanddetail"):
            return "battery_soe"

        # _LOGGER.warning("None-Typ: %s", typ)
        return None

    def get_entities_for_migrate(self):
        entity_registry = async_get_entity_registry(self._hass)
        all_entries = list(entity_registry.entities.values())

        sensors = {}

        for entry in all_entries:
            if (
                not self._current_sensors.__contains__(entry.entity_id)
                and entry.domain == "sensor"
                and "maxxi" in entry.entity_id
                and self.get_type_from_unique_id(entry.unique_id) is not None
            ):
                sensors[entry.entity_id] = entry

        return sensors

    async def async_notify_possible_migration(self):
        self._current_sensors = self.load_current_sensors()
        old_sensors = self.get_entities_for_migrate()

        # _LOGGER.warning(
        #     "Typ: %s", self.get_type_from_unique_id("Maxxicharge1-LadestandDetail")
        # )
        # return

        if not old_sensors:
            _LOGGER.info("Keine alten Sensoren zur Migration erkannt")
            return

        lines = ["Folgende alte Sensoren wurden erkannt:\n"]

        for entity_id, entry in old_sensors.items():
            lines.append(f'- old_sensor: "{entity_id}"')

            new_entity_id = self.get_new_sensor(entry)
            if new_entity_id is None:
                _LOGGER.warning(
                    "Typ: %s", self.get_type_from_unique_id(entry.unique_id)
                )

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
        await self._hass.services.async_call("recorder", "disable")
        await self._hass.async_block_till_done()

        self._current_sensors = self.load_current_sensors()
        entity_registry = async_get_entity_registry(self._hass)

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

            db_path = self._hass.config.path("home-assistant_v2.db")

            try:
                # if entity:
                #     _LOGGER.warning("%s -> %s", new_entity_id, old_entity_id)

                #     entity_registry.async_remove(old_entity_id)
                #     await self._hass.async_block_till_done()

                #     entity_registry.async_update_entity(
                #         entity_id=new_entity_id, new_entity_id=old_entity_id
                #     )
                entity_old = entity_registry.entities.get(old_entity_id)
                entity_new = entity_registry.entities.get(new_entity_id)

                if entity_old and entity_new:
                    _LOGGER.warning("%s -> %s", new_entity_id, old_entity_id)

                    # Entferne den alten Entity-Eintrag (macht den Namen frei)
                    entity_registry.async_remove(old_entity_id)
                    await self._hass.async_block_till_done()

                    self.migrate_sqlite_statistics(
                        new_entity_id, old_entity_id, db_path, False
                    )

                    # Benenne den neuen Entity-Namen auf den alten um
                    entity_registry.async_update_entity(
                        entity_id=new_entity_id, new_entity_id=old_entity_id
                    )
                    await self._hass.async_block_till_done()
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

        await self._hass.services.async_call("recorder", "enable")

        _LOGGER.info("Migration abgeschlossen.")

    def migrate_sqlite_statistics(
        self, old_sensor, new_sensor, db_path, clear_existing=True
    ):
        if old_sensor == new_sensor:
            _LOGGER.warning(
                "Alter und neuer Sensor sind identisch (%s) – keine Migration erforderlich.",
                old_sensor,
            )
            return

        if not os.path.exists(db_path):
            _LOGGER.error("SQLite-DB nicht gefunden unter: %s", db_path)
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # IDs aus statistics_meta holen
            cursor.execute(
                "SELECT id FROM statistics_meta WHERE statistic_id = ?", (old_sensor,)
            )
            old_row = cursor.fetchone()
            if not old_row:
                _LOGGER.warning("Keine Statistikdaten für alten Sensor %s", old_sensor)
                return
            old_id = old_row[0]

            cursor.execute(
                "SELECT id FROM statistics_meta WHERE statistic_id = ?", (new_sensor,)
            )
            new_row = cursor.fetchone()

            if new_row:
                new_id = new_row[0]
                _LOGGER.info(
                    "Neue Sensor-ID %s existiert bereits mit ID %s", new_sensor, new_id
                )

                if clear_existing:
                    _LOGGER.info(
                        "Lösche vorhandene Statistikdaten für %s (ID %s)",
                        new_sensor,
                        new_id,
                    )
                    for table in [
                        "statistics",
                        "statistics_short_term",
                        "statistics_runs",
                    ]:
                        cursor.execute(
                            f"DELETE FROM {table} WHERE metadata_id = ?", (new_id,)
                        )
            else:
                _LOGGER.info(
                    "Neuer Sensor %s hat noch keinen statistics_meta-Eintrag – erstelle neuen.",
                    new_sensor,
                )

                # Alten metadata-Eintrag kopieren
                cursor.execute("SELECT * FROM statistics_meta WHERE id = ?", (old_id,))
                old_meta = list(cursor.fetchone())

                # Spaltennamen ermitteln
                cursor.execute("PRAGMA table_info(statistics_meta)")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]

                # ID-Spalte entfernen, damit sie nicht eingefügt wird
                if "id" in columns:
                    id_index = columns.index("id")
                    columns.pop(id_index)
                    old_meta.pop(id_index)

                # statistic_id auf neue Entität setzen
                stat_id_index = columns.index("statistic_id")
                old_meta[stat_id_index] = new_sensor

                columns_sql = ", ".join(columns)
                placeholders = ", ".join(["?"] * len(columns))

                cursor.execute(
                    f"INSERT INTO statistics_meta ({columns_sql}) VALUES ({placeholders})",
                    tuple(old_meta),
                )
                new_id = cursor.lastrowid
                _LOGGER.info(
                    "Neuer statistics_meta-Eintrag erstellt für %s mit ID %s",
                    new_sensor,
                    new_id,
                )

            # Migration der Statistikdaten
            for table in ["statistics", "statistics_short_term"]:
                updated = cursor.execute(
                    f"UPDATE {table} SET metadata_id = ? WHERE metadata_id = ?",
                    (new_id, old_id),
                ).rowcount
                _LOGGER.info("Tabelle %s: %d Zeilen migriert.", table, updated)

            # Alten Meta-Eintrag löschen
            cursor.execute("DELETE FROM statistics_meta WHERE id = ?", (old_id,))
            _LOGGER.info("Alter statistics_meta-Eintrag (%s) gelöscht.", old_sensor)

            conn.commit()
            _LOGGER.info(
                "Statistikmigration von '%s' nach '%s' abgeschlossen.",
                old_sensor,
                new_sensor,
            )

        except Exception as e:
            _LOGGER.exception("Fehler bei Statistik-Migration: %s", e)
        finally:
            conn.close()
