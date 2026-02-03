"""Tests für das BatteryDischargeSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_discharge_sensor import BatteryDischargeSensor

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
    """BatteryDischargeSensor fixture."""
    return BatteryDischargeSensor(entry, index=0)


def test_battery_discharge_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryDischargeSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_discharge_sensor_0"
    assert sensor._attr_icon == "mdi:battery-minus-variant"
    assert sensor._attr_device_class == SensorDeviceClass.POWER
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is True


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_valid_discharge(sensor):
    """Testet die Verarbeitung gültiger Entladedaten."""
    data = {
        "batteriesInfo": [
            {
                "batteryPower": -3000  # -3kW Entladeleistung
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 3000.0  # Negativ wird positiv


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"batteryPower": -1000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_missing_battery_power(sensor):
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
async def test_battery_discharge_sensor_handle_update_none_battery_power(sensor):
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
async def test_battery_discharge_sensor_handle_update_invalid_power_value(sensor):
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
async def test_battery_discharge_sensor_handle_update_positive_power(sensor):
    """Testet Verhalten bei positivem batteryPower (Ladung)."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 2000}  # 2kW (Ladung)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (keine Entladeleistung)
    assert sensor._attr_native_value == 0


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_zero_power(sensor):
    """Testet Verhalten bei 0 Entladeleistung."""
    data = {
        "batteriesInfo": [
            {"batteryPower": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (keine Entladeleistung)
    assert sensor._attr_native_value == 0


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_extreme_power(sensor):
    """Testet Verhalten bei extremen Entladeleistungswerten."""
    data = {
        "batteriesInfo": [
            {"batteryPower": -25000}  # -25kW (über 20kW Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_discharge_sensor_handle_update_max_valid_power(sensor):
    """Testet Verhalten bei maximal gültiger Entladeleistung."""
    data = {
        "batteriesInfo": [
            {"batteryPower": -20000}  # -20kW (Grenzwert)
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
async def test_battery_discharge_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryDischargeSensor(entry, index=0)
    sensor2 = BatteryDischargeSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_discharge_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_discharge_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_discharge_sensor_string_power_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"batteryPower": "-1500"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 1500.0


@pytest.mark.asyncio
async def test_battery_discharge_sensor_small_discharge(sensor):
    """Testet kleine Entladeleistungswerte."""
    data = {
        "batteriesInfo": [
            {"batteryPower": -100}  # -100W
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 100.0
