import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

import os
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.maxxi_charge_connect.const import DOMAIN
import custom_components.maxxi_charge_connect.devices.Rssi as rssi_module
from custom_components.maxxi_charge_connect.devices.Rssi import Rssi
import pytest

from homeassistant.const import CONF_WEBHOOK_ID, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.entity import EntityCategory

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
async def test_rssi_initialization(mock_entry):
    sensor = Rssi(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_rssi"
    assert sensor._attr_icon == "mdi:wifi"
    assert sensor._attr_native_value is None
    assert sensor._attr_device_class == "signal_strength"
    assert sensor._attr_native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_rssi_add_and_handle_update():
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = Rssi(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.Rssi.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"wifiStrength": -42})
        assert sensor.native_value == -42


@pytest.mark.asyncio
async def test_rssi_will_remove_from_hass(mock_entry):
    sensor = Rssi(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None


def test_device_info(mock_entry):
    sensor = Rssi(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
