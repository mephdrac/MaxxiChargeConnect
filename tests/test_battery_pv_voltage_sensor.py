"""Tests für das BatteryPVVoltageSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricPotential

from custom_components.maxxi_charge_connect.devices.battery_pv_voltage_sensor import BatteryPVVoltageSensor

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
    """BatteryPVVoltageSensor fixture."""
    return BatteryPVVoltageSensor(entry, index=0)


def test_battery_pv_voltage_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryPVVoltageSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_pv_voltage_sensor_0"
    assert sensor._attr_icon == "mdi:alpha-v-circle"
    assert sensor._attr_device_class == SensorDeviceClass.VOLTAGE
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is False


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_valid_data(sensor):
    """Testet die Verarbeitung gültiger PV-Spannungsdaten."""
    data = {
        "batteriesInfo": [
            {
                "pvVoltage": 24000  # 24V PV-Spannung
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 24.0  # 24000mV / 1000 = 24V


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 24000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_missing_pv_voltage(sensor):
    """Testet Verhalten bei fehlendem pvVoltage."""
    data = {
        "batteriesInfo": [
            {}  # Kein pvVoltage
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_none_pv_voltage(sensor):
    """Testet Verhalten bei pvVoltage = None."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_invalid_voltage_value(sensor):
    """Testet Verhalten bei ungültigem pvVoltage Wert."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_negative_voltage(sensor):
    """Testet Verhalten bei negativer PV-Spannung."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": -12000}  # -12V PV-Spannung
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (negative PV-Spannung unplausibel)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_zero_voltage(sensor):
    """Testet Verhalten bei 0 PV-Spannung."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_extreme_voltage(sensor):
    """Testet Verhalten bei extremen PV-Spannungswerten."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 120000}  # 120V (über 100V Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_handle_update_max_valid_voltage(sensor):
    """Testet Verhalten bei maximal gültiger PV-Spannung."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 100000}  # 100V (Grenzwert)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 100.0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("maxxi_charge_connect", "test_entry_id")}
    assert device_info["name"] == "Test Entry"


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryPVVoltageSensor(entry, index=0)
    sensor2 = BatteryPVVoltageSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_pv_voltage_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_pv_voltage_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_string_voltage_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": "36000"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 36.0


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_low_voltage(sensor):
    """Testet kleine PV-Spannungswerte."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 5000}  # 5V
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 5.0


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_typical_solar_voltage(sensor):
    """Testet typische Solar-Spannungswerte."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 18000}  # 18V (typische Solar-Spannung)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 18.0


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_high_voltage_range(sensor):
    """Testet hohe PV-Spannungswerte im gültigen Bereich."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 48000}  # 48V (typische Systemspannung)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 48.0


@pytest.mark.asyncio
async def test_battery_pv_voltage_sensor_float_voltage(sensor):
    """Testet Float-Werte für PV-Spannung."""
    data = {
        "batteriesInfo": [
            {"pvVoltage": 24500.5}  # 24.5005V
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 24.5005
