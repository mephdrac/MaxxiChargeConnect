"""Discovery reuses the existing sensors instead of adding parallel measurements."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.maxxi_charge_connect.connection.mqtt_discovery import MqttDiscovery, parse_discovery
from custom_components.maxxi_charge_connect.connection.mqtt_sensor_bindings import (
    apply_legacy_value,
    legacy_binding,
    measurement_identity,
    template_path,
)
from custom_components.maxxi_charge_connect.const import CONF_DEVICE_ID, DOMAIN
from custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity import setup_discovery_entities

DEVICE = "CCU2-1020-BA5F-1F48"
MODULE = "custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity"


def spec(name="New value", source="powermeter/telemetry", template="{{ value_json.power }}", **updates):
    cfg = {
        "name": name,
        "device": {"identifiers": [DEVICE]},
        "state_topic": f"{DEVICE}/{source}",
        "value_template": template,
        "unit_of_measurement": "W",
    }
    cfg.update(updates)
    return parse_discovery(f"homeassistant/sensor/{DEVICE}/test/config", json.dumps(cfg), DEVICE)[0]


class BindingTests(unittest.TestCase):
    def test_structural_matching_survives_renamed_discovery_sensor(self):
        reading = spec(name="Completely different label", template=" {{ value_json['power'] | float(0) }} ")
        self.assertEqual(legacy_binding(reading).sensor_key, "power_meter")
        state = {}
        self.assertTrue(apply_legacy_value(state, reading, "-125"))
        self.assertEqual(state["Pr"], -125)

    def test_known_role_on_changed_topic_updates_old_pv_input(self):
        reading = spec(name="PV Power", source="firmware/new/pv", template="{{ value }}", unit_of_measurement="kW")
        state = {}
        self.assertEqual(legacy_binding(reading).sensor_key, "pv_power")
        self.assertTrue(apply_legacy_value(state, reading, "1.25"))
        self.assertEqual(state["PV_power_total"], 1250)

    def test_inverter_sign_and_legacy_clamped_power_are_preserved(self):
        reading = spec(source="inverter/telemetry")
        state = {}
        apply_legacy_value(state, reading, "-300")
        self.assertEqual(state, {"Pccu": 0, "GridChargePower": 300, "InverterPowerSigned": -300})

    def test_battery_indices_and_voltage_conversion(self):
        reading = spec(
            source="battery/telemetry", template="{{ value_json.batteries[1].voltage }}", unit_of_measurement="V"
        )
        self.assertEqual(legacy_binding(reading).sensor_key, "battery_voltage_sensor_1")
        state = {"batteriesInfo": [{"batterySOC": 20}, {"batterySOC": 80}]}
        apply_legacy_value(state, reading, "52.5")
        self.assertEqual(state["batteriesInfo"][1], {"batterySOC": 80, "batteryVoltage": 52500})
        named = spec(name="Battery 2 SOC", source="new/soc", template=None, unit_of_measurement="%")
        self.assertEqual(legacy_binding(named).sensor_key, "battery_soc_sensor_1")

    def test_same_name_with_incompatible_dimension_is_not_hidden(self):
        reading = spec(name="PV Power", source="new/topic", unit_of_measurement="%", device_class="battery")
        self.assertIsNone(legacy_binding(reading))

    def test_arithmetic_is_not_mistaken_for_raw_power(self):
        reading = spec(name="Different calculation", template="{{ value_json.power * -1 }}")
        self.assertIsNone(legacy_binding(reading))
        self.assertIsNone(template_path(reading.config["value_template"]))

    def test_discovery_aliases_share_one_measurement_identity(self):
        dot = spec(source="new/topic", template="{{ value_json.power }}")
        bracket = spec(source="new/topic", template=" {{ value_json['power'] | float }} ")
        self.assertEqual(measurement_identity(dot), measurement_identity(bracket))

    def test_energy_history_is_not_overwritten_by_ccu_counter(self):
        reading = spec(
            name="Grid Export Energy Total",
            source="new/energy",
            template=None,
            unit_of_measurement="kWh",
            state_class="total_increasing",
            device_class="energy",
        )
        self.assertEqual(legacy_binding(reading).sensor_key, "gridexportenergytotal")
        state = {"Pr": 100}
        self.assertFalse(apply_legacy_value(state, reading, "99999"))
        self.assertEqual(state, {"Pr": 100})


class EntityDeduplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/maxxi-discovery-dedup")
        registry_patch = patch(f"{MODULE}.er.async_get")
        registry_patch.start().return_value.async_get_entity_id.return_value = None
        self.addCleanup(registry_patch.stop)
        self.entry = SimpleNamespace(entry_id="one", data={CONF_DEVICE_ID: DEVICE}, async_on_unload=MagicMock())
        storage_patch = patch("custom_components.maxxi_charge_connect.connection.mqtt_discovery.Store")
        storage_patch.start().return_value.async_load = AsyncMock(return_value=None)
        self.addCleanup(storage_patch.stop)
        self.coordinator = MqttDiscovery(self.hass, self.entry, AsyncMock(), AsyncMock())
        self.hass.data[DOMAIN] = {"one": {"mqtt_discovery": self.coordinator}}
        self.add_entities = MagicMock()
        setup_discovery_entities(self.hass, self.entry, self.add_entities, "sensor")

    async def asyncTearDown(self):
        self.coordinator.stop()

    async def publish_config(self, object_id, **updates):
        config = {
            "name": "New reading",
            "device": {"identifiers": [DEVICE]},
            "state_topic": f"{DEVICE}/powermeter/telemetry",
            "value_template": "{{ value_json.power }}",
            "unit_of_measurement": "W",
        }
        config.update(updates)
        await self.coordinator.async_receive(f"homeassistant/sensor/{DEVICE}/{object_id}/config", json.dumps(config))

    async def test_covered_sensor_is_not_created_and_old_input_is_updated(self):
        await self.publish_config("renamed_meter", name="Renamed firmware sensor")
        self.add_entities.assert_not_called()
        accepted = await self.coordinator.async_receive(f"{DEVICE}/powermeter/telemetry", '{"power": -80}')
        self.assertTrue(accepted)
        old_state = {}
        self.assertTrue(self.coordinator.update_legacy_state(old_state))
        self.assertEqual(old_state["Pr"], -80)

    async def test_new_measurement_is_added_but_alias_does_not_create_another(self):
        await self.publish_config("new", state_topic=f"{DEVICE}/new/topic", value_template="{{ value_json.extra }}")
        await self.publish_config(
            "alias", state_topic=f"{DEVICE}/new/topic", value_template="{{ value_json['extra'] | float }}"
        )
        self.add_entities.assert_called_once()
        self.assertEqual(len(self.add_entities.call_args.args[0]), 1)

    async def test_duplicate_owner_is_promoted_after_withdrawal(self):
        for name in ("first", "second"):
            await self.publish_config(name, state_topic=f"{DEVICE}/new/topic", value_template="{{ value_json.extra }}")
        first = self.add_entities.call_args.args[0][0]
        await self.coordinator.async_receive(f"homeassistant/sensor/{DEVICE}/first/config", b"")
        self.assertEqual(self.add_entities.call_count, 2)
        self.assertFalse(first.available)

    async def test_only_our_prior_discovery_duplicate_is_disabled(self):
        registry = MagicMock()
        registry.async_get_entity_id.return_value = "sensor.old_discovery_copy"
        registry.async_get.return_value = SimpleNamespace(config_entry_id="one", disabled_by=None)
        with patch(f"{MODULE}.er.async_get", return_value=registry):
            await self.publish_config("known")
        registry.async_update_entity.assert_called_once_with(
            "sensor.old_discovery_copy", disabled_by=er.RegistryEntryDisabler.INTEGRATION
        )
        lookup = registry.async_get_entity_id.call_args.args
        self.assertTrue(lookup[2].startswith("one_mqtt_discovery_"))
        self.assertNotIn("power_meter", lookup[2])

    async def test_other_entries_and_user_disabled_entities_are_not_modified(self):
        registry = MagicMock()
        registry.async_get_entity_id.return_value = "sensor.some_other_entity"
        registry.async_get.return_value = SimpleNamespace(config_entry_id="different", disabled_by=None)
        with patch(f"{MODULE}.er.async_get", return_value=registry):
            await self.publish_config("known")
        registry.async_update_entity.assert_not_called()
        registry.async_get.return_value = SimpleNamespace(
            config_entry_id="one", disabled_by=er.RegistryEntryDisabler.USER
        )
        with patch(f"{MODULE}.er.async_get", return_value=registry):
            await self.publish_config("known_again")
        registry.async_update_entity.assert_not_called()

    async def test_invalid_new_message_does_not_project_a_previous_cached_value(self):
        await self.publish_config("known")
        await self.coordinator.async_receive(f"{DEVICE}/powermeter/telemetry", '{"power": 100}')
        state = {}
        self.coordinator.update_legacy_state(state)
        await self.coordinator.async_receive(f"{DEVICE}/powermeter/telemetry", "not-json")
        state["Pr"] = 200
        self.assertFalse(self.coordinator.update_legacy_state(state))
        self.assertEqual(state["Pr"], 200)
