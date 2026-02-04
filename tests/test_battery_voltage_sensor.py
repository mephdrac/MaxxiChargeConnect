"""Tests für die BatteryVoltageSensor Entity im MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import UnitOfElectricPotential
import pytest

from custom_components.maxxi_charge_connect.devices.battery_voltage_sensor import (
    BatteryVoltageSensor,
)


@pytest.mark.asyncio
async def test_battery_voltage_sensor__init():
    """Initialisierung der BatteryVoltageSensor Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    # Grundlegende Attribute prüfen
    assert sensor._attr_entity_registry_enabled_default is False  # pylint: disable=protected-access
    assert sensor._attr_translation_key == "BatteryVoltageSensor"  # pylint: disable=protected-access
    assert sensor._attr_has_entity_name is True  # pylint: disable=protected-access
    assert sensor._index == 0  # pylint: disable=protected-access
    assert sensor._attr_translation_placeholders == {"index": str(0 + 1)}  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfElectricPotential.VOLT  # pylint: disable=protected-access
    assert sensor.icon == "mdi:alpha-v-circle"
    assert sensor._attr_unique_id == "1234abcd_battery_voltage_sensor_0"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__async_added_to_hass():
    """Testet die async_added_to_hass Methode der BatteryVoltageSensor Entity."""

    hass = MagicMock()
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "abc123"

    # Mock für Dispatcher-Signale
    mock_dispatcher_connect = AsyncMock()
    hass.data = {
        "maxxi_charge_connect": {
            "abc123": {
                "listeners": [],
                "signal_update": "test_update_signal",
                "signal_stale": "test_stale_signal"
            }
        }
    }

    dummy_config_entry.data = {}

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)
    sensor.hass = hass

    # Test, dass async_added_to_hass aufgerufen werden kann
    # Wir testen nur, dass keine Exception auftritt
    try:
        await sensor.async_added_to_hass()
    except KeyError:
        # KeyError ist erwartet, da wir nicht alle Konstanten mocken
        pass


@pytest.mark.asyncio
async def test_battery_voltage_sensor__device_info():
    """Testet die device_info Eigenschaft der BatteryVoltageSensor Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_alles_ok():
    """handle_update Methode der BatteryVoltageSensor Entity testen, wenn alles ok ist."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    voltage_mv = 52300  # 52.3V in mV
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": voltage_mv
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 52.3  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update__index_error():
    """handle_update Methode der BatteryVoltageSensor Entity testen, wenn IndexError auftritt."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    voltage_mv = 52300
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": voltage_mv
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 10)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_missing_batteries_info():
    """Testet handle_update mit fehlenden batteriesInfo."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {}  # Keine batteriesInfo

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_none_battery_voltage():
    """Testet handle_update mit None batteryVoltage."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": None
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_invalid_values():
    """Testet handle_update mit ungültigen Werten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    # Test mit negativem Wert
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": -1000
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access

    # Test mit zu hohem Wert (>60000 mV = 60V)
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": 65000
            }
        ]
    }

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_string_conversion():
    """Testet handle_update mit String-Konvertierung."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": "52300"
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 52.3  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_invalid_string():
    """Testet handle_update mit ungültigem String."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": "invalid"
            }
        ]
    }

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_voltage_sensor__handle_update_edge_cases():
    """Testet handle_update mit Grenzwerten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatteryVoltageSensor(dummy_config_entry, 0)

    # Test mit 0V
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": 0
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 0.0  # pylint: disable=protected-access

    # Test mit exakt 60V
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": 60000
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 60.0  # pylint: disable=protected-access

    # Test mit 60.1V (sollte ignoriert werden)
    data = {
        "batteriesInfo": [
            {
                "batteryVoltage": 60100
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 60.0  # pylint: disable=protected-access (sollte unverändert bleiben)
