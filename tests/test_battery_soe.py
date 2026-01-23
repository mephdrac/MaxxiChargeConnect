"""Tests für die BatterySoE Entity im MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import UnitOfEnergy
import pytest
from custom_components.maxxi_charge_connect.devices.battery_soe import (
    BatterySoE,
)


@pytest.mark.asyncio
async def test_battery_soe__init():
    """ Initialisierung der BatterySoE Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoE(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class is None  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.WATT_HOUR  # pylint: disable=protected-access
    assert sensor.icon == "mdi:home-battery"
    assert sensor._attr_unique_id == "1234abcd_battery_soe"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe__device_info():
    """ device_info Property der BatterySoE Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoE(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soe_handle_update_alles_ok():
    """ _handle_update Methode der BatterySoE Entity testen, wenn alle Bedingungen erfüllt sind."""

    hass = MagicMock()
    hass.async_add_job = AsyncMock()

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
    sensor.hass = hass

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.battery_soe."
                "BatterySoE.async_write_ha_state",
                new_callable=MagicMock
            ) as mock_write_ha_state
    ):
        await sensor.handle_update(data)
        mock_write_ha_state.assert_called_once()
        assert sensor._attr_native_value == capacity  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soe__handle_update_keine_batterien():
    """ _handle_update Methode der BatterySoE Entity testen, wenn keine Batterien im Datenpaket sind."""

    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "batteriesInfo": [

        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.battery_soe.BatterySoE."
                "async_write_ha_state",
                new_callable=MagicMock
            ) as mock_write_ha_state
    ):
        await sensor.handle_update(data)
        mock_write_ha_state.assert_not_called()

        assert sensor._attr_native_value is None  # pylint: disable=protected-access
