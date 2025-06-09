import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from unittest.mock import MagicMock, patch

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.DeviceId import DeviceId
import pytest

from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory

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
async def test_DeviceId_initialization(mock_entry):
    sensor = DeviceId(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_deviceid"
    assert sensor._attr_icon == "mdi:identifier"
    assert sensor._attr_native_value is None
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_DeviceId_add_and_handle_update():
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = DeviceId(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.DeviceId.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        deviceId = "MyVersion"
        await sensor._handle_update({"deviceId": deviceId})
        assert sensor.native_value == deviceId


@pytest.mark.asyncio
async def test_DeviceId_will_remove_from_hass(mock_entry):
    sensor = DeviceId(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None


def test_device_info(mock_entry):
    sensor = DeviceId(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
