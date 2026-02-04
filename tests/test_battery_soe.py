"""Tests für die BatterySoE Entity im MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
import pytest
from custom_components.maxxi_charge_connect.devices.battery_soe import (
    BatterySoE,
)


@pytest.mark.asyncio
async def test_battery_soe__init():
    """Initialisierung der BatterySoE Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoE(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.ENERGY_STORAGE  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.WATT_HOUR  # pylint: disable=protected-access
    assert sensor.icon == "mdi:home-battery"
    assert sensor._attr_unique_id == "1234abcd_battery_soe"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe__device_info():
    """device_info Property der BatterySoE Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoE(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soe_handle_update_alles_ok():
    """handle_update Methode der BatterySoE Entity testen, wenn alle Bedingungen erfüllt sind."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    capacity = 1187.339966

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": capacity
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == capacity  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe__handle_update_keine_batterien():
    """handle_update Methode der BatterySoE Entity testen, wenn keine Batterien im Datenpaket sind."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [

        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_multiple_batteries():
    """Testet handle_update mit mehreren Batterien."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": 1000.0
            },
            {
                "batteryCapacity": 2000.0
            },
            {
                "batteryCapacity": 1500.5
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 4500.5  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_invalid_values():
    """Testet handle_update mit ungültigen Werten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    # Test mit negativem Wert
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": -100
            },
            {
                "batteryCapacity": 1000
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 1000.0  # pylint: disable=protected-access

    # Test mit zu hohem Wert (>100000 Wh)
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": 200000
            },
            {
                "batteryCapacity": 1000
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 1000.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_string_conversion():
    """Testet handle_update mit String-Konvertierung."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": "1500.5"
            },
            {
                "batteryCapacity": "2000.0"
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 3500.5  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_invalid_string():
    """Testet handle_update mit ungültigem String."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": "invalid"
            },
            {
                "batteryCapacity": 1000
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 1000.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_missing_capacity():
    """Testet handle_update mit fehlender batteryCapacity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "otherField": "value"
            },
            {
                "batteryCapacity": 1000
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 1000.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_handle_update_total_capacity_too_high():
    """Testet handle_update mit zu hoher Gesamtkapazität."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": 300000
            },
            {
                "batteryCapacity": 300000
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 0.0  # pylint: disable=protected-access
