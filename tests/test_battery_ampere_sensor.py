"""Tests für das BatteryAmpereSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_ampere_sensor import BatteryAmpereSensor

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
    """BatteryAmpereSensor fixture."""
    return BatteryAmpereSensor(entry, index=0)


def test_battery_ampere_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryAmpereSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_ampere_sensor_0"
    assert sensor._attr_icon == "mdi:alpha-a-circle"
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_valid_data(sensor):
    """Testet die Verarbeitung gültiger Batteriedaten."""
    data = {
        "batteriesInfo": [
            {
                "batteryCurrent": 5000  # 5A in mA
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 5.0  # 5000mA / 1000 = 5A


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": 1000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_missing_battery_current(sensor):
    """Testet Verhalten bei fehlendem batteryCurrent."""
    data = {
        "batteriesInfo": [
            {}  # Kein batteryCurrent
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_none_battery_current(sensor):
    """Testet Verhalten bei batteryCurrent = None."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_invalid_current_value(sensor):
    """Testet Verhalten bei ungültigem batteryCurrent Wert."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_extreme_current(sensor):
    """Testet Verhalten bei extremen Stromwerten."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": 250000}  # 250A (über 200A Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_negative_current(sensor):
    """Testet Verhalten bei negativem Stromwert."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": -5000}  # -5A
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte aktualisieren (negativer Strom ist gültig)
    assert sensor._attr_native_value == -5.0


@pytest.mark.asyncio
async def test_battery_ampere_sensor_handle_update_zero_current(sensor):
    """Testet Verhalten bei 0 Strom."""
    data = {
        "batteriesInfo": [
            {"batteryCurrent": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert device_info["name"] == "Test Entry"


@pytest.mark.asyncio
async def test_battery_ampere_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryAmpereSensor(entry, index=0)
    sensor2 = BatteryAmpereSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_ampere_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_ampere_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}
