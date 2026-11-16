"""Complete factory/source audit against anonymized real CCU discovery metadata."""

import inspect
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.core import HomeAssistant

from custom_components.maxxi_charge_connect.connection.ccu_v2_parser import parse_battery
from custom_components.maxxi_charge_connect.connection.mqtt_discovery import MqttDiscovery
from custom_components.maxxi_charge_connect.const import (
    CCU_V2,
    CONF_CCU_VERSION,
    CONF_DEVICE_ID,
    DOMAIN,
    MQTT_DIAGNOSTICS_SIGNAL,
    MQTT_DISCOVERY_COORDINATOR,
    MQTT_RECEIVE_STATS,
    MQTT_SENSOR_VALUES,
    WEBHOOK_SIGNAL_UPDATE,
)
from custom_components.maxxi_charge_connect.devices.battery_power_charge import BatteryPowerCharge
from custom_components.maxxi_charge_connect.devices.ccu_native_energy import CcuNativeEnergySensor
from custom_components.maxxi_charge_connect.devices.ccu_v2_battery_sensor_manager import CCUV2BatterySensorManager
from custom_components.maxxi_charge_connect.devices.ccu_v2_sensor_manager import V2_SENSOR_TYPES, setup_v2_sensors
from custom_components.maxxi_charge_connect.devices.mqtt_diagnostics import MqttSensorCoverageSensor
from custom_components.maxxi_charge_connect.devices.mqtt_discovery_entity import (
    DiscoveryEntity,
    setup_discovery_entities,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures/ccu_v2_discovery_anonymized.json").read_text())
DEVICE = FIXTURE["device_id"]


class CompleteMappingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/maxxi-complete-mapping")
        self.entry = SimpleNamespace(
            entry_id="complete",
            title="CCU",
            options={},
            data={CONF_DEVICE_ID: DEVICE, CONF_CCU_VERSION: CCU_V2},
            async_on_unload=MagicMock(),
        )
        storage_patch = patch("custom_components.maxxi_charge_connect.connection.mqtt_discovery.Store")
        storage_patch.start().return_value.async_load = AsyncMock(return_value=None)
        self.addCleanup(storage_patch.stop)
        self.coordinator = MqttDiscovery(self.hass, self.entry, AsyncMock(), AsyncMock())
        self.hass.data[DOMAIN] = {
            self.entry.entry_id: {
                MQTT_DISCOVERY_COORDINATOR: self.coordinator,
                WEBHOOK_SIGNAL_UPDATE: "test_legacy_update",
                MQTT_DIAGNOSTICS_SIGNAL: "test_diagnostics",
                MQTT_RECEIVE_STATS: {
                    "received_count": 0,
                    "last_received": None,
                    "last_topic": None,
                    "started_at": datetime.now(UTC),
                },
            }
        }
        for description in FIXTURE["descriptions"]:
            await self.coordinator.async_receive(description["topic"], json.dumps(description["payload"]))
        self.registry = MagicMock()
        self.registry.async_get_entity_id.side_effect = lambda domain, platform, unique: (
            None if "_mqtt_discovery_" in unique else "sensor." + unique
        )
        registry_patch = patch("homeassistant.helpers.entity_registry.async_get", return_value=self.registry)
        registry_patch.start()
        self.addCleanup(registry_patch.stop)
        # Local HA 2025 test environments predate this constructor argument;
        # the production integration targets HA 2026. Keep the real class/init.
        original_init = IntegrationSensor.__init__
        if "device_class" not in inspect.signature(original_init).parameters:

            def compatible_init(entity, *, device_class=None, **kwargs):
                original_init(entity, **kwargs)
                entity._attr_device_class = device_class

            integration_patch = patch.object(IntegrationSensor, "__init__", compatible_init)
            integration_patch.start()
            self.addCleanup(integration_patch.stop)
        self.entities = []
        setup_v2_sensors(self.hass, self.entry, self.entities.extend)
        self.battery_manager = CCUV2BatterySensorManager(self.hass, self.entry, self.entities.extend)
        self.battery_manager._process_update({"batteriesInfo": [{}, {}, {}, {}]})
        setup_discovery_entities(self.hass, self.entry, self.entities.extend, "sensor")
        setup_discovery_entities(self.hass, self.entry, self.entities.extend, "binary_sensor")

    async def asyncTearDown(self):
        self.coordinator.stop()
        for call in self.entry.async_on_unload.call_args_list:
            call.args[0]()

    async def test_every_factory_sensor_has_a_complete_source_mapping(self):
        report = self.coordinator.sensor_mapping_report()
        self.assertEqual(report["coverage"], 100)
        self.assertEqual(report["missing"], [])
        self.assertEqual(len(report["sensors"]), len(self.entities))
        self.assertEqual(len({entity.unique_id for entity in self.entities}), len(self.entities))
        self.assertFalse(any(isinstance(entity, DiscoveryEntity) for entity in self.entities))
        self.assertTrue(
            {sensor.__name__ for sensor in V2_SENSOR_TYPES}.issubset({type(e).__name__ for e in self.entities})
        )
        self.assertEqual(report["sensors"]["firmware_version"]["discovery"], ["CCU ver"])
        self.assertEqual(report["sensors"]["pv_power"]["discovery"], ["PV Power"])
        self.assertEqual(report["sensors"]["gridexportenergytotal"]["status"], "calculated")

    async def test_future_factory_sensor_without_mapping_never_claims_full_coverage(self):
        sensor = SimpleNamespace(unique_id="complete_future_sensor")
        self.coordinator.register_existing_sensors([sensor])
        report = self.coordinator.sensor_mapping_report()
        self.assertLess(report["coverage"], 100)
        self.assertIn("future_sensor", report["missing"])

    async def test_mapping_diagnostic_updates_when_factory_coverage_changes(self):
        sensor = next(e for e in self.entities if isinstance(e, MqttSensorCoverageSensor))
        sensor.hass = self.hass
        sensor.async_write_ha_state = MagicMock()
        sensor.async_on_remove = MagicMock()
        await sensor.async_added_to_hass()
        self.assertEqual(sensor.native_value, 100)
        self.coordinator.register_existing_sensors([SimpleNamespace(unique_id="complete_new_sensor")])
        self.assertLess(sensor.native_value, 100)
        self.assertIn("new_sensor", sensor.extra_state_attributes["missing"])
        self.assertIn("Licence Type", sensor.extra_state_attributes["unmapped_discovery"])
        sensor.async_write_ha_state.assert_called_once()

    async def test_ccu_energy_counters_are_separate_from_calculated_sensor_ids(self):
        native = [entity for entity in self.entities if isinstance(entity, CcuNativeEnergySensor)]
        self.assertEqual(len(native), 20)
        self.assertTrue(all(entity.unique_id.endswith("_ccu_counter") for entity in native))
        spec = next(spec for spec in self.coordinator.specs.values() if spec.name == "Grid Export Energy Total")
        await self.coordinator.async_receive(
            spec.state_topic, '{"totalEnergy":{"delivered":12345,"consumed":0},"power":0}'
        )
        counter = next(entity for entity in native if entity.native_counter_role == "gridexportenergytotal")
        self.assertAlmostEqual(counter.native_value, 12.345)
        self.assertEqual(counter.unique_id, "complete_gridexportenergytotal_ccu_counter")
        original = next(entity for entity in self.entities if entity.unique_id == "complete_gridexportenergytotal")
        self.assertNotIsInstance(original, CcuNativeEnergySensor)

    async def test_real_battery_templates_use_hardware_ids_and_pv_power_not_converter_input(self):
        message = {
            "inputPowerTotal": 900,
            "pvPowerTotal": 700,
            "socTotal": 64,
            "chargePowerTotal": 150,
            "dischargePowerTotal": 20,
            "remainWhTotal": 1234,
            "batteries": [
                {"id": 2, "soc": 80, "voltage": 53, "inputPower": 450, "pvPower": 350, "remainWh": 800},
                {"id": 1, "soc": 48, "voltage": 51, "inputPower": 450, "pvPower": 350, "remainWh": 434},
            ],
        }
        await self.coordinator.async_receive(f"{DEVICE}/battery/telemetry", json.dumps(message))
        state = {}
        self.coordinator.update_legacy_state(state)
        self.assertEqual(state["PV_power_total"], 700)
        self.assertEqual(state["batteriesInfo"][0]["batterySOC"], 48)
        self.assertEqual(state["batteriesInfo"][1]["batteryVoltage"], 53000)
        self.assertEqual(state[MQTT_SENSOR_VALUES]["battery_power_charge"], 150)
        self.assertEqual(state[MQTT_SENSOR_VALUES]["battery_power"], 130)
        parsed = parse_battery(message)
        self.assertEqual(parsed["PV_power_total"], 700)
        self.assertEqual(parsed["batteriesInfo"][0]["batterySOC"], 48)

    async def test_original_sensor_uses_its_discovered_native_measurement(self):
        entity = next(e for e in self.entities if isinstance(e, BatteryPowerCharge))
        entity.hass = self.hass
        entity.async_write_ha_state = MagicMock()
        state = {"PV_power_total": 900, "InverterPowerSigned": 300, MQTT_SENSOR_VALUES: {"battery_power_charge": 150}}
        await entity._wrapper_update(state)
        self.assertEqual(entity.unique_id, "complete_battery_power_charge")
        self.assertEqual(entity.native_value, 150)

    async def test_invalid_native_values_do_not_override_the_original_sensor(self):
        state = parse_battery({"batteries": [], "chargePowerTotal": float("nan"), "remainWhTotal": -1})
        self.assertNotIn(MQTT_SENSOR_VALUES, state)
