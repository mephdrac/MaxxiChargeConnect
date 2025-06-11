"""Testklasse."""

import logging
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

from unittest.mock import MagicMock, patch

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.firmware_version import (
    FirmwareVersion,
)
import pytest

from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Mock."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_FirmwareVersion_initialization(mock_entry):
    """Testfall."""
    sensor = FirmwareVersion(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_firmware_version"  # noqa: SLF001
    assert sensor._attr_icon == "mdi:information-outline"  # noqa: SLF001
    assert sensor._attr_native_value is None  # noqa: SLF001
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC  # noqa: SLF001


@pytest.mark.asyncio
async def test_FirmwareVersion_add_and_handle_update():
    """Test, wenn isPrOk(True)."""

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = FirmwareVersion(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.FirmwareVersion.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)  # noqa: SLF001
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        firmwareversion = "MyVersion"
        await sensor._handle_update({"firmwareVersion": firmwareversion})  # noqa: SLF001
        assert sensor.native_value == firmwareversion


@pytest.mark.asyncio
async def test_FirmwareVersion_will_remove_from_hass(mock_entry):
    """Testfall."""
    sensor = FirmwareVersion(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub  # noqa: SLF001
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None  # noqa: SLF001


def test_device_info(mock_entry):
    """Testfall."""
    sensor = FirmwareVersion(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
