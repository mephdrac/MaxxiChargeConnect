"""Test German MQTT entity names, translation hints, and wire-safe controls.

This module verifies that MQTT-discovered entities use the expected German
translations without modifying their technical identifiers or values.

The tests cover:
- German translation keys for all registered CCU V2 sensor classes.
- Translated names and source attributes of native CCU energy counters.
- Correct battery numbering in translated energy counter names.
- Translated MQTT number, select, and switch entities.
- Preservation of MQTT entity identifiers and select options.
- Completeness and consistency of translated MQTT error placeholders.

Translation files and anonymized MQTT discovery fixtures are loaded directly
from the repository to validate the actual integration resources.
"""

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

# Directory containing the German and English translation resources.
ROOT = Path(__file__).resolve().parents[1] / "custom_components/maxxi_charge_connect/translations"

# Load translations to verify the names used by Home Assistant entities.
TRANSLATIONS = {language: json.loads((ROOT / f"{language}.json").read_text()) for language in ("de", "en")}

# Load anonymized CCU V2 discovery messages used for reproducible tests.
FIXTURE = json.loads((Path(__file__).parent / "fixtures/ccu_v2_discovery_anonymized.json").read_text())

# Use the fixture's device identifier when parsing MQTT discovery messages.
DEVICE = FIXTURE["device_id"]


def platform_for(domain, language="de"):
    """Create a minimal Home Assistant platform context for translation tests.

    Home Assistant entity names depend on the platform's translation context.
    The tests instantiate entities directly, without registering them through
    a real Home Assistant entity platform.

    This helper provides the necessary platform attributes and converts the
    integration's translation definitions into the keys expected by Home
    Assistant's entity name resolution.

    Args:
        domain (str): Entity platform domain, such as ``sensor``, ``number``,
            ``select``, or ``switch``.
        language (str): Translation language to load. Defaults to German
            (``de``).

    Returns:
        SimpleNamespace: A simulated entity platform containing its domain,
        integration name, and translated entity names.

    """
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
    """Verify MQTT translations and preservation of protocol-level values.

    Tests validate German display names, translation keys, source attributes,
    stable entity identifiers, unchanged device options, and translated
    error messages.

    Entities are constructed using lightweight mock objects so the tests
    can examine translation behavior without MQTT network communication.
    """

    def setUp(self):
        """Prepare a minimal configuration entry for each translation test.

        Creates a simulated Home Assistant ConfigEntry containing the
        attributes required by the MQTT entity classes.

        The same entry identifier is used throughout the tests to ensure
        predictable entity unique IDs.
        """
        self.entry = SimpleNamespace(entry_id="translated", data={}, title="CCU", options={})

    def test_all_existing_ccu_sensor_classes_have_german_names(self):
        """Verify that every registered CCU V2 sensor has a German translation.

        Iterates over all sensor classes in ``V2_SENSOR_TYPES`` and creates
        an instance of each class.

        Each sensor's translation key must exist in the German sensor
        translation definitions.

        Individual subtests identify the sensor class if a translation
        key is missing.
        """
        for cls in V2_SENSOR_TYPES:
            entity = cls(self.entry)
            with self.subTest(sensor=cls.__name__):
                self.assertIn(entity.translation_key, TRANSLATIONS["de"]["entity"]["sensor"])

    def test_native_energy_has_a_german_ccu_source_hint(self):
        """Verify the German name and source information of a CCU energy counter.

        Creates a native CCU energy sensor representing the total exported
        grid energy.

        The test verifies:
        - The entity displays the expected German name.
        - The name identifies the CCU as the source of the counter.
        - The ``source`` attribute contains ``ccu``.
        - The entity retains its expected technical unique ID.

        Both ``platform_data`` and ``platform`` are initialized to support
        entity-name resolution across different Home Assistant versions.
        """
        spec = SimpleNamespace(key="native", config={"unit_of_measurement": "Wh"}, state_topic="ccu/state")
        coordinator = SimpleNamespace(
            entry=self.entry, specs={spec.key: spec}, native_energy_bindings={"gridexportenergytotal": spec.key}
        )
        entity = CcuNativeEnergySensor(coordinator, "gridexportenergytotal", spec)
        entity.platform_data = platform_for("sensor")
        entity.platform = entity.platform_data
        self.assertEqual(entity.name, "Netzeinspeisung gesamt (CCU-Zähler)")
        self.assertEqual(entity.extra_state_attributes["source"], "ccu")
        self.assertEqual(entity.unique_id, "translated_gridexportenergytotal_ccu_counter")

    def test_battery_counter_name_includes_the_translated_battery_number(self):
        """Verify the translated name of an individual battery energy counter.

        Creates a native energy sensor for the second battery's daily
        photovoltaic energy yield.

        The test ensures that the internal battery index is converted
        into the expected human-readable battery number and that the
        displayed German name includes the CCU counter source hint.

        Both platform attributes are initialized for compatibility with
        older and newer Home Assistant entity implementations.
        """
        spec = SimpleNamespace(key="battery", config={}, state_topic="ccu/battery")
        coordinator = SimpleNamespace(entry=self.entry, specs={}, native_energy_bindings={})
        entity = CcuNativeEnergySensor(coordinator, "battery_pv_energy_today_1", spec)
        entity.platform_data = platform_for("sensor")
        entity.platform = entity.platform_data
        self.assertEqual(entity.name, "Batterie 2 PV-Ertrag heute (CCU-Zähler)")

    def test_actual_ccu_controls_use_german_names_without_changing_ids_or_options(self):
        """Verify German MQTT control names without altering protocol values.

        Parses actual anonymized CCU V2 MQTT discovery descriptions for
        number, select, and switch entities.

        For each supported control, the test verifies:
        - The displayed entity name matches the German translation.
        - The technical unique ID remains unchanged after translation.
        - Select entities preserve the original MQTT option values.

        Preserving option values is important because translating values
        exchanged with the CCU could break device commands.

        The test also verifies that exactly seven expected control
        entities were processed.
        """
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
            entity.platform_data = platform_for(component)
            entity.platform = entity.platform_data
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
        """Verify MQTT error translations and placeholder consistency.

        Iterates over all German exception translations whose keys begin
        with ``mqtt_``.

        For each error, the test verifies:
        - The generated error uses the expected translation key.
        - The translation domain matches the integration domain.
        - The original English fallback message remains available.
        - The German and English messages use identical placeholder names.

        Placeholder consistency prevents formatting errors when Home
        Assistant renders localized error messages with dynamic values.

        Finally, the test verifies that the German MQTT confirmation
        timeout message contains the expected wording.
        """
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
