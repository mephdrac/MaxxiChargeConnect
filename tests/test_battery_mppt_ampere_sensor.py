"""Tests für das BatteryMpptAmpereSensor-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_mppt_ampere_sensor import BatteryMpptAmpereSensor

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
    """BatteryMpptAmpereSensor fixture."""
    return BatteryMpptAmpereSensor(entry, index=0)


def test_battery_mppt_ampere_sensor_initialization(sensor, entry):
    """Testet die Initialisierung des BatteryMpptAmpereSensor."""
    assert sensor._entry == entry
    assert sensor._index == 0
    assert sensor._attr_unique_id == "test_entry_id_battery_mppt_ampere_sensor_0"
    assert sensor._attr_icon == "mdi:alpha-a-circle"
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_translation_placeholders == {"index": "1"}
    assert sensor._attr_entity_registry_enabled_default is False


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_valid_data(sensor):
    """Testet die Verarbeitung gültiger MPPT-Daten."""
    data = {
        "batteriesInfo": [
            {
                "mpptCurrent": 8000  # 8A MPPT-Strom
            }
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 8.0  # 8000mA / 1000 = 8A


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_no_batteries_info(sensor):
    """Testet Verhalten bei fehlendem batteriesInfo."""
    data = {}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_empty_batteries_info(sensor):
    """Testet Verhalten bei leerem batteriesInfo."""
    data = {"batteriesInfo": []}
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_index_out_of_range(sensor):
    """Testet Verhalten bei Index außerhalb des Bereichs."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": 1000}
        ]
    }
    
    # Ändere Index auf 1 (außerhalb Bereich)
    sensor._index = 1
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_missing_mppt_current(sensor):
    """Testet Verhalten bei fehlendem mpptCurrent."""
    data = {
        "batteriesInfo": [
            {}  # Kein mpptCurrent
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_none_mppt_current(sensor):
    """Testet Verhalten bei mpptCurrent = None."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": None}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_invalid_current_value(sensor):
    """Testet Verhalten bei ungültigem mpptCurrent Wert."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": "invalid"}
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_extreme_current(sensor):
    """Testet Verhalten bei extremen MPPT-Stromwerten."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": 150000}  # 150A (über 100A Grenze)
        ]
    }
    
    await sensor.handle_update(data)
    
    # Sollte nichts aktualisieren (Plausibilitätsprüfung)
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_negative_current(sensor):
    """Testet Verhalten bei negativem MPPT-Strom."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": -5000}  # -5A MPPT-Strom
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == -5.0  # Negativer Strom ist erlaubt


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_zero_current(sensor):
    """Testet Verhalten bei 0 MPPT-Strom."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": 0}
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.0


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_handle_update_max_valid_current(sensor):
    """Testet Verhalten bei maximal gültigem MPPT-Strom."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": 100000}  # 100A (Grenzwert)
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
async def test_battery_mppt_ampere_sensor_different_indices():
    """Testet Sensoren mit unterschiedlichen Indizes."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    sensor1 = BatteryMpptAmpereSensor(entry, index=0)
    sensor2 = BatteryMpptAmpereSensor(entry, index=1)
    
    assert sensor1._attr_unique_id == "test_entry_id_battery_mppt_ampere_sensor_0"
    assert sensor1._attr_translation_placeholders == {"index": "1"}
    
    assert sensor2._attr_unique_id == "test_entry_id_battery_mppt_ampere_sensor_1"
    assert sensor2._attr_translation_placeholders == {"index": "2"}


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_string_current_conversion(sensor):
    """Testet Konvertierung von String zu float."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": "2500"}  # String statt int
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 2.5


@pytest.mark.asyncio
async def test_battery_mppt_ampere_sensor_small_current(sensor):
    """Testet kleine MPPT-Stromwerte."""
    data = {
        "batteriesInfo": [
            {"mpptCurrent": 500}  # 0.5A
        ]
    }
    
    await sensor.handle_update(data)
    
    assert sensor._attr_native_value == 0.5
