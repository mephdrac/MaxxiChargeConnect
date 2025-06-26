import logging
import os
import re
import sqlite3
import asyncio
import json
from functools import partial
# import datetime

from pathlib import Path
from datetime import datetime, timezone

from decimal import Decimal


from homeassistant.components.recorder.statistics import clear_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.components.integration.sensor import IntegrationSensor

from ..devices.pv_total_energy import PvTotalEnergy
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


ID_E_LEISTUNG = "E-Leistung"
ID_BATTERIE_LEISTUNG = "Batterie_Leistung"


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

        typ = value.lower()

        if typ.endswith("battery_power_discharge"):
            return "batterie_entladen"

        if typ.endswith("battery_soe"):
            return "ladestand_detail"

        if typ.endswith("battery_power_charge"):
            return "batterie_laden"

        if typ.endswith("battery_soc"):
            return "ladestand"

        if typ.endswith("battery_power"):
            return "batterie_leistung"

        if typ.endswith("ccu_power"):
            return "ccu_leistung"

        if typ.endswith("firmware_version"):
            return "ccu_version"

        if typ.endswith("deviceid"):
            return "deviceid"

        if typ.endswith("rssi"):
            return "wifi_signalstarke_dbm"

        if typ.endswith("pv_power"):
            return "pv_leistung"

        if typ.endswith("power_meter"):
            return "e_zaehler_leistungswert"

        if typ.endswith("grid_import"):
            return "e_zaehler_netzbezug"

        if typ.endswith("grid_export"):
            return "e_zaehler_netzeinspeisung"

        if typ.endswith("powermeterip"):
            return "konf_lok_meter_ip"

        if typ.endswith("maximumpower"):
            return "konf_lok_max_leistung"

        if typ.endswith("offlineoutputpower"):
            return "konf_lok_offline_leistung"

        if typ.endswith("numberofbatteries"):
            return "konf_lok_batterien"

        if typ.endswith("outputoffset"):
            return "konf_lok_ausgabekorrektur"

        if typ.endswith("responsetolerance"):
            return "konf_lok_reak_toleranz"

        if typ.endswith("minimumbatterydischarge"):
            return "konf_lok_min_soc"

        if typ.endswith("maximumbatterycharge"):
            return "konf_lok_max_soc"

        # if typ.endswith("konf_lok_meter_auto"):
        #     return None

        if typ.endswith("powermetertype"):
            return "konf_lok_meter_manu"

        if typ.endswith("dc/dc-algorithmus"):
            return "konf_dc_algorithm"

        if typ.endswith("microinverter"):
            return "konf_wr"

        if typ.endswith("ccuspeed"):
            return "konf_ccu_speed"

        if typ.endswith("cloudservice"):
            return "konf_lok_cloud"

        if typ.endswith("localserver"):
            return "konf_lok_lserver"

        if typ.endswith("apiroute"):
            return "konf_api_route"

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
            return "rssi"

        if typ.endswith("pv_leistung"):
            return "pv_power"

        if typ.endswith("e-leistung"):
            return "power_meter"

        if typ.endswith("e_zaehler_netzbezug"):
            return "grid_import"

        if typ.endswith("e_zaehler_netzeinspeisung"):
            return "grid_export"

        if typ.endswith("ladestanddetail"):
            return "battery_soe"

        if typ.endswith("konf_lok_meter_ip"):
            return "powermeterip"

        if typ.endswith("konf_lok_max_leistung"):
            return "maximumpower"

        if typ.endswith("konf_lok_offline_leistung"):
            return "offlineoutputpower"

        if typ.endswith("konf_lok_batterien"):
            return "numberofbatteries"

        if typ.endswith("konf_lok_ausgabekorrektur"):
            return "outputoffset"

        if typ.endswith("konf_lok_reak_toleranz"):
            return "responsetolerance"

        if typ.endswith("konf_lok_min_soc"):
            return "minimumbatterydischarge"

        if typ.endswith("konf_lok_max_soc"):
            return "maximumbatterycharge"

        # if typ.endswith("konf_lok_meter_auto"):
        #     return None

        if typ.endswith("konf_lok_meter_manu"):
            return "powermetertype"

        if typ.endswith("konf_dc_algorithm"):
            return "dc/dc-algorithmus"

        if typ.endswith("konf_wr"):
            return "microinverter"

        if typ.endswith("konf_ccu_speed"):
            return "ccuspeed"

        if typ.endswith("konf_lok_cloud"):
            return "cloudservice"

        if typ.endswith("konf_lok_lserver"):
            return "localserver"

        if typ.endswith("konf_api_route"):
            return "apiroute"

        return None

    def get_riemann_entities_for_migrate(self):
        entity_registry = async_get_entity_registry(self._hass)
        all_entries = list(entity_registry.entities.values())

        sensors_temp = {}
        sensors_temp2 = {}
        sensors_kwh = {}

        RIEMANN_LIST = {
            ("BatterieLaden_1", "batterytotalenergycharge"),
            ("E-Zaehler_Netzbezug1", "gridimportenergytotal"),
            ("E-Zaehler Netzeinspeisung", "gridexportenergytotal"),
            ("Akku_Entladen_1", "batterytotalenergydischarge"),
            ("PV_Leistung", "pvtotalenergy"),
        }

        for entry in all_entries:
            for key, key_neu in RIEMANN_LIST:
                if entry.unique_id.endswith(key):
                    # _LOGGER.warning("Key found: %s", entry.entity_id)
                    # _LOGGER.warning(
                    #     "Riemann: %s",
                    #     self.find_integral_helpers_by_input_sensor(entry.entity_id),
                    # )
                    sensors_temp[key] = self.find_integral_helpers_by_input_sensor(
                        entry.entity_id
                    )
                elif entry.unique_id.lower().endswith(key_neu):
                    sensors_temp2[key] = entry

        for key, entry in sensors_temp.items():
            if sensors_temp2.__contains__(key) and entry is not None:
                sensors_kwh[entry.entity_id] = (entry, sensors_temp2[key])

        return sensors_kwh

    def get_entities_for_migrate(self):
        entity_registry = async_get_entity_registry(self._hass)
        all_entries = list(entity_registry.entities.values())

        sensors = {}

        for entry in all_entries:
            typ = self.get_type_from_unique_id(entry.unique_id)
            if (
                not self._current_sensors.__contains__(entry.entity_id)
                and entry.domain == "sensor"
                and "maxxi" in entry.entity_id
                and typ is not None
                and typ
                not in {
                    "batterytotalenergycharge",
                    "batterytotalenergydischarge",
                    "gridimportenergytotal",
                    "gridexportenergytotal",
                    "pvtotalenergy",
                }
            ):
                sensors[entry.entity_id] = entry

        return sensors

    def resolve_entity_id_from_unique_id(self, unique_id: str):
        registry = async_get_entity_registry(self._hass)

        for entry in registry.entities.values():
            if entry.unique_id.lower().endswith(unique_id.lower()):
                return entry.entity_id
        return None

    async def async_notify_possible_migration(self):
        self._current_sensors = self.load_current_sensors()
        old_sensors = self.get_entities_for_migrate()
        riemann_sensors = self.get_riemann_entities_for_migrate()

        # _LOGGER.warning(
        #     "Typ: %s", self.get_type_from_unique_id("Maxxicharge1-LadestandDetail")
        # )
        # return

        if not old_sensors and not riemann_sensors:
            _LOGGER.info("Keine alten Sensoren zur Migration erkannt")
            return

        lines = ["Folgende alte Riemann-Sensoren wurden erkannt:\n"]

        for entity_id, (old_entry, new_entry) in riemann_sensors.items():
            lines.append(f'- old_sensor: "{old_entry.entity_id}"')

            if new_entry:
                lines.append(f'  new_sensor: "{new_entry.entity_id}"')
            else:
                lines.append(f'  new_sensor: "sensor.HIER_EINTRAGEN"')

        lines.append("\n\nFolgende alte Sensoren wurden erkannt:\n")
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
            "ACHTUNG: Immer zuerst die Riemann-Sensoren migrieren.\n\n"
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

            typ, old_type, entity = sensor_info

            # if typ or not entity:
            #     _LOGGER.warning(
            #         "Sensor-Typ von %s konnte nicht erkannt werden", new_entity_id
            #     )
            #     continue

            # sensor_map[old_type] = new_entity_id
            _LOGGER.warning(
                "Mapping: %s → %s (Typ: %s)", old_entity_id, new_entity_id, typ
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
                    _LOGGER.info("%s -> %s", new_entity_id, old_entity_id)

                    # Entferne den alten Entity-Eintrag (macht den Namen frei)
                    # entity_registry.async_remove(old_entity_id)
                    # await self._hass.async_block_till_done()

                    await self.migrate_states_meta(db_path, old_entity_id, entity)
                    await self._hass.async_block_till_done()

                    self.migrate_logbook_entries(db_path, old_entity_id, new_entity_id)

                    # # Spezialbehandlung von Statistics
                    # if typ == "batterytotalenergydischarge":
                    #     self.migrate_negative_statistics(
                    #         db_path,
                    #         self.resolve_entity_id_from_unique_id(ID_BATTERIE_LEISTUNG),
                    #         new_entity_id,
                    #     )
                    # elif typ == "gridexportenergytotal":
                    #     self.migrate_negative_statistics(
                    #         db_path,
                    #         self.resolve_entity_id_from_unique_id(ID_E_LEISTUNG),
                    #         new_entity_id,
                    #     )

                    # elif typ == "gridimportenergytotal":
                    #     self.migrate_positive_statistics(
                    #         db_path,
                    #         self.resolve_entity_id_from_unique_id(ID_E_LEISTUNG),
                    #         new_entity_id,
                    #     )
                    # elif typ == "batterytotalenergycharge":
                    #     self.migrate_positive_statistics(
                    #         db_path,
                    #         self.resolve_entity_id_from_unique_id(ID_BATTERIE_LEISTUNG),
                    #         new_entity_id,
                    #     )

                    # else:

                    self.migrate_sqlite_statistics(
                        old_entity_id, new_entity_id, db_path, False
                    )
                    # self.migrate_positive_statistics(
                    #     db_path, old_entity_id, new_entity_id
                    # )

                    # self.migrate_positive_statistics(
                    #     db_path, old_entity_id, new_entity_id
                    # )
                    # self.migrate_state_history(db_path, old_entity_id, new_entity_id)

                    await self._hass.async_block_till_done()
                    await self.async_replace_entity_ids_in_yaml_files(
                        old_entity_id=old_entity_id, new_entity_id=new_entity_id
                    )

                    # # Benenne den neuen Entity-Namen auf den alten um
                    # entity_registry.async_update_entity(
                    #     entity_id=new_entity_id, new_entity_id=old_entity_id
                    # )
                    await self._hass.async_block_till_done()

                    entity_registry.async_remove(old_entity_id)
                    await self._hass.async_block_till_done()

                else:
                    _LOGGER.error("Neuer Unique-Key konnte nicht gesetzt werden")
                    return
            except Exception as e:
                _LOGGER.error("Fehler beim Umbenennen der Entity: %s", e)

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

    async def migrate_states_meta(self, db_path, old_entity_id, entity_new):
        if not os.path.exists(db_path):
            _LOGGER.error("Recorder-DB nicht gefunden unter: %s", db_path)
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            new_entity_id = entity_new.entity_id

            # # IDs holen
            # cursor.execute(
            #     "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
            #     (new_entity_id,),
            # )
            # neu_row = cursor.fetchone()
            # if not neu_row:
            #     _LOGGER.warning("Keine states_meta für %s gefunden.", new_entity_id)
            # else:
            #     neu_id = neu_row[0]

            #     cursor.execute(
            #         "delete from states where metadata_id = ?",
            #         (neu_id,),
            #     )
            #     deleted_rows = cursor.rowcount

            # _LOGGER.warning("%s Zeilen gelöscht.", deleted_rows)

            # IDs holen
            cursor.execute(
                "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
                (old_entity_id,),
            )
            old_row = cursor.fetchone()
            if not old_row:
                _LOGGER.warning("Keine states_meta für %s gefunden.", old_entity_id)
                return
            old_id = old_row[0]

            cursor.execute(
                "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
                (new_entity_id,),
            )
            new_row = cursor.fetchone()

            if new_row:
                new_id = new_row[0]
            else:
                cursor.execute(
                    "INSERT INTO states_meta (entity_id) VALUES (?)", (new_entity_id,)
                )
                new_id = cursor.lastrowid
                _LOGGER.info(
                    "states_meta für %s erstellt mit ID %s", new_entity_id, new_id
                )

            # States umhängen
            updated = cursor.execute(
                "UPDATE states SET metadata_id = ? WHERE metadata_id = ?",
                (new_id, old_id),
            ).rowcount

            # get Last valid value
            cursor.execute(
                "SELECT s.state FROM states_meta sm INNER JOIN states s ON sm.metadata_id = s.metadata_id WHERE sm.entity_id = ? and (s.state != 'unavailable' and s.state != 'unknown') order by s.last_updated_ts desc LIMIT 1",
                (new_entity_id,),
            )
            cur_row = cursor.fetchone()

            if not cur_row:
                _LOGGER.warning("Keine gültigen states für %s gefunden.", new_entity_id)
                return
            cur_valid_state = cur_row[0]

            # IDs holen
            cursor.execute(
                "SELECT state_id FROM states_meta sm INNER JOIN states s ON sm.metadata_id = s.metadata_id WHERE sm.entity_id = ? order by last_updated_ts desc LIMIT 1",
                (new_entity_id,),
            )
            cur_row = cursor.fetchone()
            if not cur_row:
                _LOGGER.warning("Keine states_meta für %s gefunden.", new_entity_id)
                return
            cur_state_id = cur_row[0]

            cursor.execute(
                "update states set state=? where state_id = ?",
                (
                    cur_valid_state,
                    cur_state_id,
                ),
            )
            updated_rows = cursor.rowcount

            _LOGGER.warning("%s Zeilen geupdatet.", updated_rows)

            conn.commit()

            sensor = self._hass.data[DOMAIN].get(entity_new.unique_id)
            if sensor is not None:
                sensor.set_state_from_migration(cur_valid_state)

            _LOGGER.info(
                "States: %d Einträge migriert von %s nach %s.",
                updated,
                old_entity_id,
                new_entity_id,
            )

        except Exception as e:
            _LOGGER.exception("Fehler bei State-Migration (states_meta): %s", e)
        finally:
            conn.close()

    def migrate_state_history(self, db_path, old_entity_id, new_entity_id):
        _LOGGER.info("Migrate State History ...")

        if not os.path.exists(db_path):
            _LOGGER.error("Recorder-DB nicht gefunden unter: %s", db_path)
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Neuesten Zustand des alten Sensors holen
            cursor.execute(
                """
                SELECT * FROM states
                WHERE entity_id = ?
                ORDER BY last_updated_ts DESC
                LIMIT 1
                """,
                (old_entity_id,),
            )
            row = cursor.fetchone()

            # Spaltennamen holen
            cursor.execute("PRAGMA table_info(states)")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]

            # 'state_id' statt 'id'
            if "state_id" in columns:
                id_idx = columns.index("state_id")
                columns.pop(id_idx)
                if row:
                    row = list(row)
                    row.pop(id_idx)
            else:
                _LOGGER.warning("'state_id' nicht gefunden – fahre trotzdem fort.")

            if row:
                # entity_id anpassen
                entity_id_index = columns.index("entity_id")
                row[entity_id_index] = new_entity_id

                placeholders = ", ".join(["?"] * len(row))
                cursor.execute(
                    f"INSERT INTO states ({', '.join(columns)}) VALUES ({placeholders})",
                    row,
                )
                _LOGGER.info(
                    "Letzter Zustand von %s → %s migriert.",
                    old_entity_id,
                    new_entity_id,
                )
            else:
                _LOGGER.warning(
                    "Kein letzter Zustand für %s gefunden – Erzeuge Dummy-Zustand",
                    old_entity_id,
                )

                now = datetime.now().isoformat()
                cursor.execute(
                    """
                    INSERT INTO states (
                        entity_id, state, last_changed, last_updated, attributes
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (new_entity_id, "0", now, now, "{}"),
                )
                _LOGGER.info("Dummy-Zustand für %s erzeugt (0)", new_entity_id)

            conn.commit()

            # self.update_restore_state(new_entity_id, Decimal("0"))

        except Exception as e:
            _LOGGER.exception("Fehler bei State-Migration: %s", e)
        finally:
            conn.close()

            _LOGGER.info("Migrate State History ...abgeschlossen")

    def migrate_logbook_entries(self, db_path, old_entity_id, new_entity_id):
        if not os.path.exists(db_path):
            _LOGGER.error("Recorder-DB nicht gefunden unter: %s", db_path)
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            old_json = f'"{old_entity_id}"'
            new_json = f'"{new_entity_id}"'

            cursor.execute(
                """
                UPDATE events
                SET event_data = REPLACE(event_data, ?, ?)
                WHERE event_type = 'state_changed'
                AND event_data LIKE ?
                """,
                (old_json, new_json, f"%{old_json}%"),
            )
            count = cursor.rowcount
            conn.commit()

            _LOGGER.info(
                "Logbuch: %d Einträge von %s nach %s migriert.",
                count,
                old_entity_id,
                new_entity_id,
            )

        except Exception as e:
            _LOGGER.exception("Fehler bei Logbuch-Migration: %s", e)
        finally:
            conn.close()

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

    async def async_replace_entity_ids_in_yaml_files(
        self, old_entity_id: str, new_entity_id: str
    ) -> None:
        await asyncio.to_thread(
            self._replace_entity_ids_in_yaml_files_blocking,
            old_entity_id,
            new_entity_id,
        )

    def _replace_entity_ids_in_yaml_files_blocking(
        self, old_entity_id, new_entity_id, base_path=None
    ):
        """Durchsucht alle .yaml-Dateien im config-Verzeichnis nach der alten Entity-ID und ersetzt sie durch die neue."""
        if base_path is None:
            base_path = self._hass.config.config_dir

        replaced_files = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if not file.endswith(".yaml"):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if old_entity_id in content:
                        new_content = re.sub(
                            rf"\b{re.escape(old_entity_id)}\b",
                            new_entity_id,
                            content,
                        )
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

                        _LOGGER.info("Ersetzt in Datei: %s", file_path)
                        replaced_files.append(file_path)
                except Exception as e:
                    _LOGGER.error("Fehler beim Bearbeiten von %s: %s", file_path, e)

        if replaced_files:
            _LOGGER.info(
                "Ersetzungen abgeschlossen in %d Datei(en)", len(replaced_files)
            )
        else:
            _LOGGER.info("Keine YAML-Dateien mit %s gefunden", old_entity_id)

    def migrate_positive_statistics(
        self, db_path, old_sensor, new_sensor, clear_existing=True
    ):
        if old_sensor == new_sensor:
            _LOGGER.warning("Quelle und Ziel identisch – abgebrochen")
            return
        if not os.path.exists(db_path):
            _LOGGER.error("DB nicht gefunden: %s", db_path)
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # IDs besorgen
        cur.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id=?", (old_sensor,)
        )
        row = cur.fetchone()
        if not row:
            _LOGGER.info("Kein statistics_meta für %s", old_sensor)
            return
        old_id = row[0]

        cur.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id=?", (new_sensor,)
        )
        row = cur.fetchone()

        if row:
            new_id = row[0]
            if clear_existing:
                for tbl in ("statistics", "statistics_short_term"):
                    cur.execute(f"DELETE FROM {tbl} WHERE metadata_id=?", (new_id,))
                _LOGGER.info("Alte Daten von %s gelöscht.", new_sensor)
        else:
            # meta kopieren
            cur.execute("SELECT * FROM statistics_meta WHERE id=?", (old_id,))
            meta = list(cur.fetchone())
            cur.execute("PRAGMA table_info(statistics_meta)")
            cols = [c[1] for c in cur.fetchall()]
            id_idx = cols.index("id")
            stat_idx = cols.index("statistic_id")
            shared_idx = cols.index("shared_attrs") if "shared_attrs" in cols else None

            cols.pop(id_idx)
            meta.pop(id_idx)
            meta[stat_idx - 1] = new_sensor
            if shared_idx is not None:
                meta[shared_idx - 1] = json.dumps(
                    {
                        "state_class": "measurement",
                        "device_class": "power",
                        "unit_of_measurement": "W",
                    }
                )

            ph = ", ".join("?" * len(meta))
            cur.execute(
                f"INSERT INTO statistics_meta ({', '.join(cols)}) VALUES ({ph})", meta
            )
            new_id = cur.lastrowid
            _LOGGER.info("statistics_meta angelegt für %s, ID: %s", new_sensor, new_id)

        # Daten kopieren + transformieren (nur positive Werte)
        for tbl in ("statistics", "statistics_short_term"):
            cur.execute(f"SELECT * FROM {tbl} WHERE metadata_id=?", (old_id,))
            rows = cur.fetchall()
            if not rows:
                continue

            cur.execute(f"PRAGMA table_info({tbl})")
            tcols = [c[1] for c in cur.fetchall()]
            id_idx = tcols.index("id")
            meta_idx = tcols.index("metadata_id")

            inserted = 0
            for r in rows:
                r = list(r)
                r.pop(id_idx)
                r[meta_idx - 1] = new_id
                for name in ("state", "mean", "min", "max", "sum"):
                    if name in tcols:
                        i = tcols.index(name)
                        v = r[i - 1]
                        r[i - 1] = v if v is not None and v > 0 else 0.0
                cur.execute(
                    f"INSERT INTO {tbl} ({', '.join(c for i, c in enumerate(tcols) if i != id_idx)}) VALUES ({', '.join('?' * len(r))})",
                    r,
                )
                inserted += 1
            _LOGGER.info("%s Zeilen in %s kopiert.", inserted, tbl)

        conn.commit()
        conn.close()
        _LOGGER.info("Fertig! Home Assistant neu starten.")

    def migrate_negative_statistics(
        self, db_path, old_sensor, new_sensor, clear_existing=True
    ):
        if old_sensor == new_sensor:
            _LOGGER.warning("Quelle und Ziel identisch – abgebrochen")
            return
        if not os.path.exists(db_path):
            _LOGGER.error("DB nicht gefunden: %s", db_path)
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # IDs besorgen
        cur.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id=?", (old_sensor,)
        )
        row = cur.fetchone()
        if not row:
            _LOGGER.info("Kein statistics_meta für %s", old_sensor)
            return
        old_id = row[0]

        cur.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id=?", (new_sensor,)
        )
        row = cur.fetchone()

        if row:
            new_id = row[0]
            if clear_existing:
                for tbl in ("statistics", "statistics_short_term"):
                    cur.execute(f"DELETE FROM {tbl} WHERE metadata_id=?", (new_id,))
                _LOGGER.info("Alte Daten von %s gelöscht", new_sensor)
        else:
            # meta kopieren
            cur.execute("SELECT * FROM statistics_meta WHERE id=?", (old_id,))
            meta = list(cur.fetchone())
            cur.execute("PRAGMA table_info(statistics_meta)")
            cols = [c[1] for c in cur.fetchall()]
            id_idx = cols.index("id")
            stat_idx = cols.index("statistic_id")
            # optional shared_attrs
            shared_idx = cols.index("shared_attrs") if "shared_attrs" in cols else None

            cols.pop(id_idx)
            meta.pop(id_idx)
            meta[stat_idx - 1] = new_sensor
            if shared_idx is not None:
                meta[shared_idx - 1] = json.dumps(
                    {
                        "state_class": "measurement",
                        "device_class": "power",
                        "unit_of_measurement": "W",
                    }
                )

            ph = ", ".join("?" * len(meta))
            cur.execute(
                f"INSERT INTO statistics_meta ({', '.join(cols)}) VALUES ({ph})", meta
            )
            new_id = cur.lastrowid
            _LOGGER.info("statistics_meta angelegt für %s, ID: %s", new_sensor, new_id)

        # Daten kopieren + transformieren
        for tbl in ("statistics", "statistics_short_term"):
            cur.execute(f"SELECT * FROM {tbl} WHERE metadata_id=?", (old_id,))
            rows = cur.fetchall()
            if not rows:
                continue

            cur.execute(f"PRAGMA table_info({tbl})")
            tcols = [c[1] for c in cur.fetchall()]
            id_idx = tcols.index("id")
            meta_idx = tcols.index("metadata_id")

            inserted = 0
            for r in rows:
                r = list(r)
                r.pop(id_idx)
                r[meta_idx - 1] = new_id
                for name in ("state", "mean", "min", "max", "sum"):
                    if name in tcols:
                        i = tcols.index(name)
                        v = r[i - 1]
                        r[i - 1] = abs(v) if v is not None and v < 0 else 0.0
                cur.execute(
                    f"INSERT INTO {tbl} ({', '.join(c for i, c in enumerate(tcols) if i != id_idx)}) VALUES ({', '.join('?' * len(r))})",
                    r,
                )
                inserted += 1
            _LOGGER.info("%s Zeilen in %s kopiert.", inserted, tbl)

        conn.commit()
        conn.close()
        _LOGGER.info("Fertig! Home Assistant neu starten.")

    def find_integral_helpers_by_input_sensor(self, input_entity_id: str):
        # _LOGGER.warning("Suche kwh - Sensor für: %s", input_entity_id)
        for entity in self._hass.data["sensor"].entities:
            if isinstance(entity, IntegrationSensor):
                # _LOGGER.warning("Found: %s, %s", entity._source_entity, input_entity_id)
                if entity._source_entity == input_entity_id:
                    _LOGGER.debug(
                        "Found: %s, %s", entity._source_entity, entity.entity_id
                    )
                    return entity

        return None
        # entity_registry = async_get_entity_registry(self._hass)
        result = []

        # for entry in entity_registry.entities.values():
        #     if entry.platform != "integration":
        #         continue
        #     if not entry.entity_id.startswith("sensor."):
        #         continue
        #     if entry.domain != "sensor":
        #         continue

        #     # Auf Integralsensor prüfen
        #     if entry.original_icon != "mdi:chart-histogram":
        #         continue

        #     # _LOGGER.warning("Integrasensor gefunden. %s", entry.entity_id)
        #     # Konfigurationsquelle auslesen
        #     # options = entry.options.get("sensor", {})
        #     # input_id = options.get("source")

        #     # _LOGGER.warning("Found: %s, %s", entry.entity_id, entry.options)

        #     # if input_id == input_entity_id:
        #     #     result.append(entry.entity_id)

        #     # Hole zugehörige ConfigEntry
        #     config_entry = self._hass.config_entries.async_get_entry(
        #         entry.config_entry_id
        #     )
        #     if not config_entry or config_entry.domain != "integration":
        #         continue

        #     _LOGGER.warning("Found: %s, %s", entry.entity_id, config_entry)

        #     # Jetzt schauen, ob dieser Helper unseren Sensor als Quelle hat
        #     source = config_entry.data.get("source")
        #     if source == input_entity_id:
        #         result.append(entry.entity_id)

        return result

    async def update_restore_state(self, entity_id: str, new_value: Decimal):
        """Aktualisiert state / native_value / last_valid_state in core.restore_state."""
        restore_file = Path(self._hass.config.path(".storage/core.restore_state"))

        if not restore_file.exists():
            _LOGGER.warning("%s fehlt – nichts zu patchen", restore_file)
            return

        try:
            # data = json.loads(restore_file.read_text(encoding="utf-8"))
            # Nicht blockierend lesen

            # Partial mit benanntem Argument
            read_func = partial(restore_file.read_text, encoding="utf-8")
            raw = await self._hass.async_add_executor_job(read_func)

            data = json.loads(raw)

            if (
                not isinstance(data, dict)
                or "data" not in data
                or not isinstance(data["data"], list)
            ):
                _LOGGER.error("Unerwartiges Format in restore_state – Abbruch")
                return

            entries = data["data"]
            now_iso = datetime.now(timezone.utc).isoformat()
            val_str = str(new_value)

            # passenden Eintrag suchen
            entry = next(
                (e for e in entries if e["state"]["entity_id"] == entity_id), None
            )

            if entry is None:
                _LOGGER.warning(
                    "Kein restore_state-Eintrag für %s – lege neuen an", entity_id
                )
                entry = {
                    "state": {
                        "entity_id": entity_id,
                        "state": val_str,
                        "attributes": {},
                        "last_changed": now_iso,
                        "last_reported": now_iso,
                        "last_updated": now_iso,
                        "context": {"id": "", "parent_id": None, "user_id": None},
                    },
                    "extra_data": {
                        "native_value": {
                            "__type": "<class 'decimal.Decimal'>",
                            "decimal_str": val_str,
                        },
                        "native_unit_of_measurement": None,
                        "source_entity": None,
                        "last_valid_state": val_str,
                    },
                    "last_seen": now_iso,
                }
                entries.append(entry)
            else:
                # vorhandenen Eintrag patchen
                entry["state"]["state"] = val_str
                entry["state"]["last_changed"] = now_iso
                entry["state"]["last_updated"] = now_iso
                entry["state"]["last_reported"] = now_iso

                nv = {
                    "__type": "<class 'decimal.Decimal'>",
                    "decimal_str": val_str,
                }
                entry["extra_data"]["native_value"] = nv
                entry["extra_data"]["last_valid_state"] = val_str
                entry["last_seen"] = now_iso

            # restore_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

            new_data = json.dumps(data, indent=2)
            write_func = partial(restore_file.write_text, new_data, encoding="utf-8")
            await self._hass.async_add_executor_job(write_func)
            _LOGGER.info("restore_state für %s ⇒ %s aktualisiert", entity_id, val_str)

        except Exception as e:
            _LOGGER.exception("Fehler beim Patchen von restore_state: %s", e)
