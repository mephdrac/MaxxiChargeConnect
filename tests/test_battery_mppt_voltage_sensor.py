"""Tests für das BatteryMpptVoltageSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricPotential

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_mppt_voltage_sensor import BatteryMpptVoltageSensor

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
    """BatteryMpptVoltageSensor fixture."""
    return BatteryMpptVoltageSensor(entry, index=0)


def test_battery_mppt_voltage_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryMpptVoltageSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_mppt_voltage_sensor_0"
    assert sensor._attr_icon == "mdi:alpha-v-circle"
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is False


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_valid_data(sensor):
    """Testet die Verarbeitung gültiger MPPT-Spannungsdaten."""
    data = {
        "batteriesInfo": [
            {
                "mpptVoltage": 48000  # 48V MPPT-Spannung
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 48.0  # 48000mV / 1000 = 48V


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 48000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_missing_mppt_voltage(sensor):
    """Testet Verhalten bei fehlendem mpptVoltage."""
    data = {
        "batteriesInfo": [
            {}  # Kein mpptVoltage
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_none_mppt_voltage(sensor):
    """Testet Verhalten bei mpptVoltage = None."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_invalid_voltage_value(sensor):
    """Testet Verhalten bei ungültigem mpptVoltage Wert."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_negative_voltage(sensor):
    """Testet Verhalten bei negativer MPPT-Spannung."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": -1000}  # -1V MPPT-Spannung
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (negative Spannung unplausibel)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_zero_voltage(sensor):
    """Testet Verhalten bei 0 MPPT-Spannung."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_extreme_voltage(sensor):
    """Testet Verhalten bei extremen MPPT-Spannungswerten."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 150000}  # 150V (über 100V Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_handle_update_max_valid_voltage(sensor):
    """Testet Verhalten bei maximal gültiger MPPT-Spannung."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 100000}  # 100V (Grenzwert)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 100.0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert device_info["name"] == "Test Entry"


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryMpptVoltageSensor(entry, index=0)
    sensor2 = BatteryMpptVoltageSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_mppt_voltage_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_mppt_voltage_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_string_voltage_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": "24000"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 24.0


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_low_voltage(sensor):
    """Testet kleine MPPT-Spannungswerte."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 12000}  # 12V
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 12.0


@pytest.mark.asyncio
async def test_battery_mppt_voltage_sensor_typical_solar_voltage(sensor):
    """Testet typische Solar-Spannungswerte."""
    data = {
        "batteriesInfo": [
            {"mpptVoltage": 36000}  # 36V (typische Solar-Spannung)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 36.0
