"""German names, source hints and wire-safe translated MQTT controls."""

import json
import string
import unittest
from pathlib import Path
from types import SimpleNamespace

from custom_components.maxxi_charge_connect.connection.mqtt_discovery import parse_discovery
from custom_components.maxxi_charge_connect.connection.mqtt_errors import mqtt_error
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.ccu_native_energy import CcuNativeEnergySensor
from custom_components.maxxi_charge_connect.devices.ccu_v2_sensor_manager import V2_SENSOR_TYPES
from custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity import (
    DiscoveryNumber,
    DiscoverySelect,
    DiscoverySwitch,
)

ROOT = Path(__file__).resolve().parents[1] / "custom_components/maxxi_charge_connect/translations"
TRANSLATIONS = {language: json.loads((ROOT / f"{language}.json").read_text()) for language in ("de", "en")}
FIXTURE = json.loads((Path(__file__).parent / "fixtures/ccu_v2_discovery_anonymized.json").read_text())
DEVICE = FIXTURE["device_id"]


def platform_for(domain, language="de"):
    names = TRANSLATIONS[language]["entity"][domain]
    return SimpleNamespace(
        domain=domain,
        platform_name=DOMAIN,
        component_translations={},
        platform_translations={
            f"component.{DOMAIN}.entity.{domain}.{key}.name": entry["name"] for key, entry in names.items()
        },
    )


class MqttTranslationTests(unittest.TestCase):
    def setUp(self):
        self.entry = SimpleNamespace(entry_id="translated", data={}, title="CCU", options={})

    def test_all_existing_ccu_sensor_classes_have_german_names(self):
        for cls in V2_SENSOR_TYPES:
            entity = cls(self.entry)
            with self.subTest(sensor=cls.__name__):
                self.assertIn(entity.translation_key, TRANSLATIONS["de"]["entity"]["sensor"])

    def test_native_energy_has_a_german_ccu_source_hint(self):
        spec = SimpleNamespace(key="native", config={"unit_of_measurement": "Wh"}, state_topic="ccu/state")
        coordinator = SimpleNamespace(
            entry=self.entry, specs={spec.key: spec}, native_energy_bindings={"gridexportenergytotal": spec.key}
        )
        entity = CcuNativeEnergySensor(coordinator, "gridexportenergytotal", spec)
        entity.platform = platform_for("sensor")
        self.assertEqual(entity.name, "Netzeinspeisung gesamt (CCU-Zähler)")
        self.assertEqual(entity.extra_state_attributes["source"], "ccu")
        self.assertEqual(entity.unique_id, "translated_gridexportenergytotal_ccu_counter")

    def test_battery_counter_name_includes_the_translated_battery_number(self):
        spec = SimpleNamespace(key="battery", config={}, state_topic="ccu/battery")
        coordinator = SimpleNamespace(entry=self.entry, specs={}, native_energy_bindings={})
        entity = CcuNativeEnergySensor(coordinator, "battery_pv_energy_today_1", spec)
        entity.platform = platform_for("sensor")
        self.assertEqual(entity.name, "Batterie 2 PV-Ertrag heute (CCU-Zähler)")

    def test_actual_ccu_controls_use_german_names_without_changing_ids_or_options(self):
        expected = {
            "Minimum SOC": "Minimaler Ladestand",
            "Maximum SOC": "Maximaler Ladestand",
            "Maximum Output": "Maximale Ausgangsleistung",
            "Meter Loss Output": "Ausgangsleistung bei Zählerausfall",
            "Maximum Charging Power": "Maximale Ladeleistung",
            "Charging Strategy": "Ladestrategie",
            "UPS Mode": "USV-Modus",
        }
        count = 0
        for item in FIXTURE["descriptions"]:
            component = item["topic"].split("/")[1]
            if component not in ("number", "select", "switch"):
                continue
            spec = parse_discovery(item["topic"], json.dumps(item["payload"]), DEVICE)[0]
            coordinator = SimpleNamespace(entry=self.entry, specs={spec.key: spec})
            cls = {"number": DiscoveryNumber, "select": DiscoverySelect, "switch": DiscoverySwitch}[component]
            entity = cls(coordinator, spec)
            identity = entity.unique_id
            entity.platform = platform_for(component)
            self.assertEqual(entity.name, expected[spec.name])
            self.assertEqual(entity.unique_id, identity)
            if component == "select":
                self.assertEqual(
                    entity.options,
                    ["Automatic", "Time Plan", "Price Plan"],
                )
            count += 1
        self.assertEqual(count, 7)

    def test_mqtt_error_translations_and_placeholders_are_complete(self):
        for key, entry in TRANSLATIONS["de"]["exceptions"].items():
            if not key.startswith("mqtt_"):
                continue
            error = mqtt_error(key, "English fallback", seconds=10)
            self.assertEqual(error.translation_key, key)
            self.assertEqual(error.translation_domain, DOMAIN)
            self.assertEqual(str(error), "English fallback")
            placeholders = lambda text: {field for _, field, _, _ in string.Formatter().parse(text) if field}
            self.assertEqual(
                placeholders(entry["message"]), placeholders(TRANSLATIONS["en"]["exceptions"][key]["message"])
            )
        self.assertIn("bestätigt", TRANSLATIONS["de"]["exceptions"]["mqtt_confirmation_timeout"]["message"])
