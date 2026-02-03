"""Tests für das BatteryChargeSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_charge_sensor import BatteryChargeSensor

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test Entry"
    entry.data = {"webhook_id": "abc123"}
    return entry


@pytest.fixture
def sensor(entry):
    """BatteryChargeSensor fixture."""
    return BatteryChargeSensor(entry, index=0)


def test_battery_charge_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryChargeSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_charge_sensor_0"
    assert sensor._attr_icon == "mdi:battery-plus-variant"
    assert sensor._attr_device_class == SensorDeviceClass.POWER
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is True


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_valid_charge(sensor):
    """Testet die Verarbeitung gültiger Ladedaten."""
    data = {
        "batteriesInfo": [
            {
                "batteryPower": 5000  # 5kW Ladeleistung
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 5000.0


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 1000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_missing_battery_power(sensor):
    """Testet Verhalten bei fehlendem batteryPower."""
    data = {
        "batteriesInfo": [
            {}  # Kein batteryPower
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_none_battery_power(sensor):
    """Testet Verhalten bei batteryPower = None."""
    data = {
        "batteriesInfo": [
            {"batteryPower": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_invalid_power_value(sensor):
    """Testet Verhalten bei ungültigem batteryPower Wert."""
    data = {
        "batteriesInfo": [
            {"batteryPower": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_negative_power(sensor):
    """Testet Verhalten bei negativem batteryPower (Entladung)."""
    data = {
        "batteriesInfo": [
            {"batteryPower": -2000}  # -2kW (Entladung)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (keine Ladeleistung)
    assert sensor._attr_native_value == 0


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_zero_power(sensor):
    """Testet Verhalten bei 0 Ladeleistung."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_extreme_power(sensor):
    """Testet Verhalten bei extremen Ladeleistungswerten."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 25000}  # 25kW (über 20kW Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_charge_sensor_handle_update_max_valid_power(sensor):
    """Testet Verhalten bei maximal gültiger Ladeleistung."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 20000}  # 20kW (Grenzwert)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 20000.0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert device_info["name"] == "Test Entry"


@pytest.mark.asyncio
async def test_battery_charge_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryChargeSensor(entry, index=0)
    sensor2 = BatteryChargeSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_charge_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_charge_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_charge_sensor_string_power_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"batteryPower": "3500"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 3500.0
