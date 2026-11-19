"""Tests for NumberConfigEntity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.core import Event

from custom_components.maxxi_charge_connect.const import (
    DOMAIN,
    EVENT_SUMMER_MIN_CHARGE_CHANGED,
    WINTER_MODE_CHANGED_EVENT,
)
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
    entity.hass = hass
    entity.platform = MagicMock()
    entity.platform.platform_name = "test_platform"
    entity.platform.domain = DOMAIN
    coordinator.data = {"test_key": 42.5}
    return entity


def test_initialization(number_entity):
    """Test that NumberConfigEntity initializes correctly."""
    assert number_entity._attr_unique_id.endswith("_testRest")
    assert number_entity._attr_native_min_value == 0
    assert number_entity._attr_native_max_value == 100
    assert number_entity._attr_native_step == 1
    assert number_entity._attr_native_unit_of_measurement == "%"
    assert str(number_entity._attr_entity_category) == "config"
    assert number_entity._attr_mode == "box"


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
async def test_async_added_to_hass(number_entity):
    """Test async_added_to_hass registers listeners."""
    number_entity.async_on_remove = MagicMock()
    number_entity._coordinator.async_add_listener = MagicMock()

    await number_entity.async_added_to_hass()

    number_entity._coordinator.async_add_listener.assert_called_once()
    assert number_entity.async_on_remove.called


@pytest.mark.asyncio
async def test_set_native_value_success(number_entity):
    """Test successful set_native_value with mocked HTTP POST."""
    number_entity.async_write_ha_state = MagicMock()
    with patch.object(number_entity, "_send_config_to_device", return_value=True):
        result = await number_entity.async_set_native_value(75.0)
        assert result is True


@pytest.mark.asyncio
async def test_set_native_value_failure(number_entity):
    """Test set_native_value when HTTP POST fails."""
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


def test_handle_winter_mode_changed(number_entity, entry):
    """Refresh the state when this CCU's winter mode changes."""
    number_entity.async_write_ha_state = MagicMock()
    event = Event(
        WINTER_MODE_CHANGED_EVENT,
        {"entry_id": entry.entry_id, "enabled": True},
    )

    number_entity._handle_winter_mode_changed(event)

    number_entity.async_write_ha_state.assert_called_once()


def test_handle_winter_mode_changed_foreign_entry(number_entity):
    """Do not refresh state for a different CCU's winter mode event."""
    number_entity.async_write_ha_state = MagicMock()
    event = Event(
        WINTER_MODE_CHANGED_EVENT,
        {"entry_id": "other_entry", "enabled": True},
    )

    number_entity._handle_winter_mode_changed(event)

    number_entity.async_write_ha_state.assert_not_called()


def test_handle_summer_charge_changed_valid(number_entity, entry):
    """Apply valid summer charge events originating from this CCU."""
    number_entity.set_native_value = MagicMock()
    number_entity.async_write_ha_state = MagicMock()
    number_entity._depends_on_winter_mode = True
    event = Event(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"entry_id": entry.entry_id, "value": "25.5"},
    )

    number_entity._handle_summer_charge_changed(event)

    number_entity.set_native_value.assert_called_once_with(25.5)
    number_entity.async_write_ha_state.assert_called_once()


def test_handle_summer_charge_changed_invalid(number_entity, entry):
    """Ignore invalid summer charge values from this CCU."""
    number_entity.set_native_value = MagicMock()
    number_entity.async_write_ha_state = MagicMock()
    number_entity._depends_on_winter_mode = True
    event = Event(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"entry_id": entry.entry_id, "value": "invalid"},
    )

    number_entity._handle_summer_charge_changed(event)

    number_entity.set_native_value.assert_not_called()


def test_handle_summer_charge_changed_foreign_entry(number_entity):
    """Do not apply a different CCU's summer charge setting."""
    number_entity.set_native_value = MagicMock()
    number_entity.async_write_ha_state = MagicMock()
    number_entity._depends_on_winter_mode = True
    event = Event(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"entry_id": "other_entry", "value": "25.5"},
    )

    number_entity._handle_summer_charge_changed(event)

    number_entity.set_native_value.assert_not_called()
    number_entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_async_will_remove_from_hass(number_entity):
    """Test cleanup on removal."""
    number_entity._remove_listener = MagicMock()
    number_entity._remove_summer_listener = MagicMock()

    await number_entity.async_will_remove_from_hass()

    number_entity._remove_listener.assert_called_once()
    number_entity._remove_summer_listener.assert_called_once()
