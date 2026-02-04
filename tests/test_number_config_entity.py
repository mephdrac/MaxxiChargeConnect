"""Tests für NumberConfigEntity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.http_post.number_config_entity import (
    NumberConfigEntity,
)


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Device"
    entry.data = {"ip_address": "192.168.1.100"}
    return entry


@pytest.fixture
def coordinator():
    """Mock coordinator."""
    coord = MagicMock()
    coord.data = {"test_key": 42.5}
    coord.entry = MagicMock()
    coord.entry.entry_id = "test_entry"
    return coord


@pytest.fixture
def number_entity(hass, entry, coordinator):
    """Create a NumberConfigEntity instance for testing."""
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}
    entity = NumberConfigEntity(
        hass=hass,
        entry=entry,
        translation_key="test_key",
        rest_key="testRest",
        value_key="test_key",
        min_value=0,
        max_value=100,
        step=1,
        unit="%",
        depends_on_winter_mode=False,
    )
    entity.hass = hass  # Ensure hass is set
    # Set up required platform_data attribute
    entity.platform = MagicMock()
    entity.platform.platform_name = "test_platform"
    entity.platform.domain = DOMAIN
    # Reset coordinator data to known state
    coordinator.data = {"test_key": 42.5}
    return entity


def test_initialization(number_entity):
    """Test that NumberConfigEntity initializes correctly."""
    # The unique_id is generated using coordinator.entry.entry_id which is a MagicMock
    # So we just check that it ends with our rest_key
    assert number_entity._attr_unique_id.endswith("_testRest")
    assert number_entity._attr_native_min_value == 0
    assert number_entity._attr_native_max_value == 100
    assert number_entity._attr_native_step == 1
    assert number_entity._attr_native_unit_of_measurement == "%"
    assert str(number_entity._attr_entity_category) == "config"  # EntityCategory enum
    assert number_entity._attr_mode == "box"


# def test_native_value_from_coordinator(number_entity, coordinator):
#     """Test that native_value reads from coordinator."""
#     # The coordinator data is already set in the fixture
#     # Reset the _show_current_value_immediately flag to ensure we read from coordinator
#     number_entity._show_current_value_immediately = False
#     # The as_float function extracts numbers from strings, so it should return 42.5
#     # But since the coordinator is a MagicMock, we need to check the actual behavior
#     coordinator.data = {"test_key": "42.5"}
#     assert number_entity.native_value == 42.5


# def test_native_value_no_coordinator_data(number_entity, coordinator):
#     """Test native_value when coordinator has no data."""
#     coordinator.data = {}
#     number_entity._show_current_value_immediately = False
#     assert number_entity.native_value is None


def test_native_value_show_immediately(number_entity):
    """Test _show_current_value_immediately flag."""
    number_entity._attr_native_value = 99.9
    number_entity._show_current_value_immediately = True
    assert number_entity.native_value == 99.9
    assert number_entity._show_current_value_immediately is False


def test_device_info(number_entity):
    """Test device_info property."""
    info = number_entity.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry")}
    assert info["name"] == "Test Device"


@pytest.mark.asyncio
async def test_async_added_to_hass(number_entity, hass):
    """Test async_added_to_hass registers listeners."""
    number_entity.async_on_remove = MagicMock()
    number_entity._coordinator.async_add_listener = MagicMock()

    await number_entity.async_added_to_hass()

    number_entity._coordinator.async_add_listener.assert_called_once()
    assert number_entity.async_on_remove.called


@pytest.mark.asyncio
async def test_set_native_value_success(number_entity):
    """Test successful set_native_value with mocked HTTP POST."""
    # Mock the async_write_ha_state to avoid platform_data issues
    number_entity.async_write_ha_state = MagicMock()
    with patch.object(number_entity, "_send_config_to_device", return_value=True):
        result = await number_entity.async_set_native_value(75.0)
        assert result is True


@pytest.mark.asyncio
async def test_set_native_value_failure(number_entity):
    """Test set_native_value when HTTP POST fails."""
    # Mock the async_write_ha_state to avoid platform_data issues
    number_entity.async_write_ha_state = MagicMock()
    with patch.object(number_entity, "_send_config_to_device", return_value=False):
        result = await number_entity.async_set_native_value(75.0)
        assert result is False


@pytest.mark.asyncio
async def test_send_config_to_device_success(number_entity):
    """Test _send_config_to_device successful HTTP POST."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="OK")

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response
        # Mock coordinator.async_request_refresh to be async
        number_entity._coordinator.async_request_refresh = AsyncMock()
        result = await number_entity._send_config_to_device(50.0)
        assert result is True


@pytest.mark.asyncio
async def test_send_config_to_device_http_error(number_entity):
    """Test _send_config_to_device handles HTTP errors."""
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response
        # Mock coordinator.async_request_refresh to be async
        number_entity._coordinator.async_request_refresh = AsyncMock()
        result = await number_entity._send_config_to_device(50.0)
        assert result is False


@pytest.mark.asyncio
async def test_send_config_to_device_connection_error(number_entity):
    """Test _send_config_to_device handles connection errors."""
    with patch("aiohttp.ClientSession.post", side_effect=ClientError("Connection failed")):
        result = await number_entity._send_config_to_device(50.0)
        assert result is False


@pytest.mark.asyncio
async def test_send_config_to_device_no_ip(number_entity):
    """Test _send_config_to_device when IP address is missing."""
    number_entity._ip = ""
    result = await number_entity._send_config_to_device(50.0)
    assert result is False


@pytest.mark.asyncio
async def test_handle_winter_mode_changed(number_entity):
    """Test _handle_winter_mode_changed triggers state write."""
    number_entity.async_write_ha_state = MagicMock()
    number_entity._handle_winter_mode_changed({})
    number_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_summer_charge_changed_valid(number_entity):
    """Test _handle_summer_charge_changed with valid value."""
    number_entity.set_native_value = MagicMock()
    number_entity.async_write_ha_state = MagicMock()

    event = MagicMock()
    event.data = {"value": "25.5"}

    number_entity._depends_on_winter_mode = True
    number_entity._handle_summer_charge_changed(event)

    number_entity.set_native_value.assert_called_once_with(25.5)


@pytest.mark.asyncio
async def test_handle_summer_charge_changed_invalid(number_entity):
    """Test _handle_summer_charge_changed with invalid value."""
    number_entity.set_native_value = MagicMock()
    number_entity.async_write_ha_state = MagicMock()

    event = MagicMock()
    event.data = {"value": "invalid"}

    number_entity._depends_on_winter_mode = True
    number_entity._handle_summer_charge_changed(event)

    number_entity.set_native_value.assert_not_called()


@pytest.mark.asyncio
async def test_async_will_remove_from_hass(number_entity):
    """Test cleanup on removal."""
    number_entity._remove_listener = MagicMock()
    number_entity._remove_summer_listener = MagicMock()

    await number_entity.async_will_remove_from_hass()

    number_entity._remove_listener.assert_called_once()
    number_entity._remove_summer_listener.assert_called_once()
