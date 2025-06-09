import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

import os
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.PvPower import PvPower
import pytest

from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

print("cwd =", os.getcwd())
print("sys.path =", sys.path)

_LOGGER = logging.getLogger(__name__)


# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_pv_power_initialization(mock_entry):
    sensor = PvPower(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_pv_power"
    assert sensor._attr_icon == "mdi:solar-power"
    assert sensor._attr_native_value is None
    assert sensor._attr_device_class == SensorDeviceClass.POWER
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update1():
    """Test, wenn isPowerTotalOk is True."""

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PvPower(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.PvPower.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.PvPower.isPowerTotalOk"
        ) as mock_isPowerTotalOk,
    ):
        mock_isPowerTotalOk.return_value = True

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"PV_power_total": 234.675})
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update2():
    """Test, wenn isPowerTotalOk is False."""

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PvPower(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.PvPower.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.PvPower.isPowerTotalOk"
        ) as mock_isPowerTotalOk,
    ):
        mock_isPowerTotalOk.return_value = False

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"PV_power_total": 234})
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_pv_power_will_remove_from_hass(mock_entry):
    sensor = PvPower(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None


def test_device_info(mock_entry):
    sensor = PvPower(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
