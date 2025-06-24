import logging
import os
import re
import sqlite3
import asyncio
import json

from homeassistant.components.recorder.statistics import clear_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry


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

        if typ.endswith("batterytotalenergycharge"):
            return "batterie_laden_kwh"

        if typ.endswith("batterytotalenergydischarge"):
            return "batterie_entladen_kwh"

        if typ.endswith("gridimportenergytotal"):
            return "e_zaehler_netzbezug_kwh"

        if typ.endswith("gridexportenergytotal"):
            return "e_zaehler_netzeinspeisung_kwh"

        if typ.endswith("pvtotalenergy"):
            return "pv_leistung_kwh"

        if typ.endswith("battery_state_of_energy"):
            return "pv_leistung_kwh"

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

        # Riemann
        if typ.endswith("batterytotalenergycharge"):
            return "batterieladen_1"

        if typ.endswith("batterytotalenergydischarge"):
            return "akku_entladen_1"

        if typ.endswith("gridimportenergytotal"):
            return "e-zaehler_netzbezug1"

        if typ.endswith("gridexportenergytotal"):
            return "e-zaehler netzeinspeisung"

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

        # Riemann
        if typ.endswith("batterieladen_1"):
            return "batterytotalenergycharge"

        if typ.endswith("akku_entladen_1"):
            return "batterytotalenergydischarge"

        if typ.endswith("e-zaehler_netzbezug1"):
            return "gridimportenergytotal"

        if typ.endswith("e-zaehler netzeinspeisung"):
            return "gridexportenergytotal"

        # _LOGGER.warning("None-Typ: %s", typ)
        return None

    def get_riemann_entities_for_migrate(self):
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
                in {
                    "batterytotalenergycharge",
                    "batterytotalenergydischarge",
                    "gridimportenergytotal",
                    "gridexportenergytotal",
                }
            ):
                sensors[entry.entity_id] = entry

        return sensors

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

        for entity_id, entry in riemann_sensors.items():
            lines.append(f'- old_sensor: "{entity_id}"')

            new_entity_id = self.get_new_sensor(entry)
            if new_entity_id is None:
                _LOGGER.warning(
                    "Typ: %s", self.get_type_from_unique_id(entry.unique_id)
                )

                lines.append(f'  new_sensor: "sensor.HIER_EINTRAGEN"')
            else:
                lines.append(f'  new_sensor: "{new_entity_id}"')

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

            if not old_type or not entity:
                _LOGGER.warning(
                    "Sensor-Typ von %s konnte nicht erkannt werden", new_entity_id
                )
                continue

            sensor_map[old_type] = new_entity_id
            _LOGGER.info(
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

                    self.migrate_states_meta(db_path, old_entity_id, new_entity_id)
                    self.migrate_logbook_entries(db_path, old_entity_id, new_entity_id)

                    # Spezialbehandlung von Statistics
                    if typ == "batterytotalenergydischarge":
                        self.migrate_negative_statistics(
                            db_path,
                            self.resolve_entity_id_from_unique_id(ID_BATTERIE_LEISTUNG),
                            new_entity_id,
                        )
                    elif typ == "gridexportenergytotal":
                        self.migrate_negative_statistics(
                            db_path,
                            self.resolve_entity_id_from_unique_id(ID_E_LEISTUNG),
                            new_entity_id,
                        )

                    elif typ == "gridimportenergytotal":
                        self.migrate_positive_statistics(
                            db_path,
                            self.resolve_entity_id_from_unique_id(ID_E_LEISTUNG),
                            new_entity_id,
                        )
                    elif typ == "batterytotalenergycharge":
                        self.migrate_positive_statistics(
                            db_path,
                            self.resolve_entity_id_from_unique_id(ID_BATTERIE_LEISTUNG),
                            new_entity_id,
                        )

                    else:
                        self.migrate_sqlite_statistics(
                            old_entity_id, new_entity_id, db_path, False
                        )

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

    def migrate_states_meta(self, db_path, old_entity_id, new_entity_id):
        if not os.path.exists(db_path):
            _LOGGER.error("Recorder-DB nicht gefunden unter: %s", db_path)
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

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

            conn.commit()
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

    # def migrate_state_history(self, db_path, old_entity_id, new_entity_id):
    #     if not os.path.exists(db_path):
    #         _LOGGER.error("Recorder-DB nicht gefunden unter: %s", db_path)
    #         return

    #     try:
    #         conn = sqlite3.connect(db_path)
    #         cursor = conn.cursor()

    #         cursor.execute(
    #             """
    #             UPDATE states
    #             SET entity_id = ?
    #             WHERE entity_id = ?
    #             """,
    #             (new_entity_id, old_entity_id),
    #         )
    #         count = cursor.rowcount
    #         conn.commit()

    #         _LOGGER.info(
    #             "States: %d Einträge von %s nach %s migriert.",
    #             count,
    #             old_entity_id,
    #             new_entity_id,
    #         )

    #     except Exception as e:
    #         _LOGGER.exception("Fehler bei State-Migration: %s", e)
    #     finally:
    #         conn.close()

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
