"""Tests für das BatteryPVPowerSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from custom_components.maxxi_charge_connect.devices.battery_pv_power_sensor import BatteryPVPowerSensor

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
    """BatteryPVPowerSensor fixture."""
    return BatteryPVPowerSensor(entry, index=0)


def test_battery_pv_power_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryPVPowerSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_pv_power_sensor_0"
    assert sensor._attr_icon == "mdi:alpha-v-circle"
    assert sensor._attr_device_class == SensorDeviceClass.POWER
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is False


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_valid_data(sensor):
    """Testet die Verarbeitung gültiger PV-Leistungsdaten."""
    data = {
        "batteriesInfo": [
            {
                "pvPower": 5000  # 5000W PV-Leistung
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 5000.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"pvPower": 5000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_missing_pv_power(sensor):
    """Testet Verhalten bei fehlendem pvPower."""
    data = {
        "batteriesInfo": [
            {}  # Kein pvPower
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_none_pv_power(sensor):
    """Testet Verhalten bei pvPower = None."""
    data = {
        "batteriesInfo": [
            {"pvPower": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_invalid_power_value(sensor):
    """Testet Verhalten bei ungültigem pvPower Wert."""
    data = {
        "batteriesInfo": [
            {"pvPower": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_negative_power(sensor):
    """Testet Verhalten bei negativer PV-Leistung."""
    data = {
        "batteriesInfo": [
            {"pvPower": -1000}  # -1000W PV-Leistung
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (negative PV-Leistung unplausibel)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_zero_power(sensor):
    """Testet Verhalten bei 0 PV-Leistung."""
    data = {
        "batteriesInfo": [
            {"pvPower": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_extreme_power(sensor):
    """Testet Verhalten bei extremen PV-Leistungswerten."""
    data = {
        "batteriesInfo": [
            {"pvPower": 15000}  # 15kW (über 10kW Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_handle_update_max_valid_power(sensor):
    """Testet Verhalten bei maximal gültiger PV-Leistung."""
    data = {
        "batteriesInfo": [
            {"pvPower": 10000}  # 10kW (Grenzwert)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 10000.0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    device_info = sensor.device_info
    assert device_info["identifiers"] == {("maxxi_charge_connect", "test_entry_id")}
    assert device_info["name"] == "Test Entry"


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryPVPowerSensor(entry, index=0)
    sensor2 = BatteryPVPowerSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_pv_power_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_pv_power_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_string_power_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"pvPower": "2500"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 2500.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_low_power(sensor):
    """Testet kleine PV-Leistungswerte."""
    data = {
        "batteriesInfo": [
            {"pvPower": 100}  # 100W
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 100.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_typical_solar_power(sensor):
    """Testet typische Solar-Leistungswerte."""
    data = {
        "batteriesInfo": [
            {"pvPower": 3000}  # 3kW (typische Solar-Leistung)
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 3000.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_float_zero_value(sensor):
    """Testet, dass float(0) korrekt behandelt wird (früheres Problem mit 'or 0.0')."""
    data = {
        "batteriesInfo": [
            {"pvPower": 0}  # 0 als int, wird zu 0.0 als float
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_pv_power_sensor_string_zero_value(sensor):
    """Testet, dass "0" als String korrekt behandelt wird."""
    data = {
        "batteriesInfo": [
            {"pvPower": "0"}  # "0" als String
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0
