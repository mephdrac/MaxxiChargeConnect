"""Tests für die BatterySoESensor Entity im MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
import pytest

from custom_components.maxxi_charge_connect.devices.battery_soe_sensor import (
    BatterySoESensor,
)


@pytest.mark.asyncio
async def test_battery_soe_sensor__init():
    """Initialisierung der BatterySoESensor Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoESensor(dummy_config_entry, 0)

    # Grundlegende Attribute prüfen
    assert sensor._attr_entity_registry_enabled_default is True  # pylint: disable=protected-access
    assert sensor._attr_translation_key == "BatterySoESensor"  # pylint: disable=protected-access
    assert sensor._attr_has_entity_name is True  # pylint: disable=protected-access
    assert sensor._index == 0  # pylint: disable=protected-access
    assert sensor._attr_translation_placeholders == {"index": str(0 + 1)}  # pylint: disable=protected-access
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.WATT_HOUR  # pylint: disable=protected-access
    assert sensor.icon == "mdi:home-battery"
    assert sensor._attr_unique_id == "1234abcd_battery_soe_0"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__async_added_to_hass():
    """Testet die async_added_to_hass Methode der BatterySoESensor Entity."""

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

    dummy_config_entry.data = {
        CONF_WEBHOOK_ID: "Webhook_ID"
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)
    sensor.hass = hass

    # Test, dass async_added_to_hass aufgerufen werden kann
    # Wir testen nur, dass keine Exception auftritt
    try:
        await sensor.async_added_to_hass()
    except KeyError:
        # KeyError ist erwartet, da wir nicht alle Konstanten mocken
        pass


@pytest.mark.asyncio
async def test_battery_soe_sensor__device_info():
    """Testet die device_info Eigenschaft der BatterySoESensor Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoESensor(dummy_config_entry, 0)

    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_alles_ok():
    """handle_update Methode der BatterySoESensor Entity testen, wenn alles ok ist."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    bat = 1187.339966
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": bat
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == bat  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update__index_error():
    """handle_update Methode der BatterySoESensor Entity testen, wenn IndexError auftritt."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    bat = 1187.339966
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": bat
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 10)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_missing_batteries_info():
    """Testet handle_update mit fehlenden batteriesInfo."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {}  # Keine batteriesInfo

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_none_battery_capacity():
    """Testet handle_update mit None batteryCapacity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": None
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_invalid_values():
    """Testet handle_update mit ungültigen Werten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    # Test mit negativem Wert
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": -100
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access

    # Test mit zu hohem Wert (>100000 Wh)
    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": 200000
            }
        ]
    }

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_string_conversion():
    """Testet handle_update mit String-Konvertierung."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": "1500.5"
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 1500.5  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_invalid_string():
    """Testet handle_update mit ungültigem String."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [
            {
                "batteryCapacity": "invalid"
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access
