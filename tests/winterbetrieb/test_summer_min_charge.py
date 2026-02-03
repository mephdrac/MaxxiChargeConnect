"""Tests für SummerMinCharge."""

from unittest.mock import MagicMock, patch
import pytest

from custom_components.maxxi_charge_connect.winterbetrieb.summer_min_charge import (
    SummerMinCharge,
)
from custom_components.maxxi_charge_connect.const import (
    CONF_SUMMER_MIN_CHARGE,
    DEFAULT_SUMMER_MIN_CHARGE,
    WINTER_MODE_CHANGED_EVENT,
    EVENT_SUMMER_MIN_CHARGE_CHANGED,
    CONF_WINTER_MODE,
    DOMAIN,
)


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"
    entry.options = {CONF_SUMMER_MIN_CHARGE: 25}
    return entry


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def summer_min_charge(entry, hass):
    """Create SummerMinCharge instance for testing."""
    entity = SummerMinCharge(entry)
    entity.hass = hass
    return entity


def test_initialization(summer_min_charge, entry):
    """Test that SummerMinCharge initializes correctly."""
    assert summer_min_charge._entry == entry
    assert summer_min_charge._attr_unique_id == "test_entry_summer_min_charge"
    assert summer_min_charge._attr_icon == "mdi:battery-lock"
    assert summer_min_charge._attr_entity_category.name == "CONFIG"
    assert summer_min_charge._attr_native_unit_of_measurement == "%"
    assert summer_min_charge.attr_native_min_value == 0
    assert summer_min_charge._attr_native_step == 1
    assert summer_min_charge._attr_native_max_value == 100
    assert summer_min_charge._attr_native_value == 25


def test_initialization_with_default_value(entry, hass):
    """Test initialization with default value when not in options."""
    entry.options = {}
    entity = SummerMinCharge(entry)
    entity.hass = hass
    
    assert entity._attr_native_value == DEFAULT_SUMMER_MIN_CHARGE


def test_set_native_value(summer_min_charge):
    """Test set_native_value method."""
    with patch.object(summer_min_charge, 'async_set_native_value', new_callable=MagicMock) as mock_async_set:
        mock_async_set.return_value = None
        summer_min_charge.set_native_value(30)
        mock_async_set.assert_called_once_with(30)
        # The method returns the coroutine from async_set_native_value
        # We can't compare coroutines directly, so we just verify it was called correctly


@pytest.mark.asyncio
async def test_async_set_native_value(summer_min_charge, hass, entry):
    """Test async_set_native_value method."""
    value = 35
    
    # Mock async_write_ha_state to avoid HA integration issues
    summer_min_charge.async_write_ha_state = MagicMock()
    
    await summer_min_charge.async_set_native_value(value)
    
    assert summer_min_charge._attr_native_value == value
    assert hass.data[DOMAIN][CONF_SUMMER_MIN_CHARGE] == value
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={
            **entry.options,
            CONF_SUMMER_MIN_CHARGE: value,
        },
    )
    summer_min_charge.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass(summer_min_charge, hass):
    """Test async_added_to_hass method."""
    # Mock async_write_ha_state to avoid HA integration issues
    summer_min_charge.async_write_ha_state = MagicMock()
    
    await summer_min_charge.async_added_to_hass()
    
    hass.bus.async_listen.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        summer_min_charge._handle_winter_mode_changed
    )
    assert summer_min_charge._remove_listener is not None
    summer_min_charge.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_will_remove_from_hass(summer_min_charge):
    """Test async_will_remove_from_hass method."""
    mock_listener = MagicMock()
    summer_min_charge._remove_listener = mock_listener
    
    await summer_min_charge.async_will_remove_from_hass()
    
    mock_listener.assert_called_once()
    # The method doesn't set _remove_listener to None, it just calls it
    assert summer_min_charge._remove_listener == mock_listener


def test_notify_dependents(summer_min_charge, hass):
    """Test _notify_dependents method."""
    summer_min_charge._attr_native_value = 40
    
    summer_min_charge._notify_dependents()
    
    hass.bus.async_fire.assert_called_once_with(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"value": 40}
    )


def test_notify_dependents_no_value(summer_min_charge, hass):
    """Test _notify_dependents method with None value."""
    summer_min_charge._attr_native_value = None
    
    summer_min_charge._notify_dependents()
    
    hass.bus.async_fire.assert_not_called()


def test_available_winter_mode_disabled(summer_min_charge, hass):
    """Test available property when winter mode is disabled."""
    hass.data[DOMAIN][CONF_WINTER_MODE] = False
    
    assert summer_min_charge.available is True


def test_available_winter_mode_enabled(summer_min_charge, hass):
    """Test available property when winter mode is enabled."""
    hass.data[DOMAIN][CONF_WINTER_MODE] = True
    
    assert summer_min_charge.available is False


def test_available_winter_mode_missing(summer_min_charge, hass):
    """Test available property when winter mode key is missing."""
    # CONF_WINTER_MODE not in hass.data[DOMAIN]
    
    assert summer_min_charge.available is True


def test_handle_winter_mode_changed_winter_disabled(summer_min_charge, hass):
    """Test _handle_winter_mode_changed when winter mode is disabled."""
    event = MagicMock()
    event.data = {"enabled": False}
    
    # Mock async_write_ha_state to avoid HA integration issues
    summer_min_charge.async_write_ha_state = MagicMock()
    
    with patch.object(summer_min_charge, '_notify_dependents') as mock_notify:
        summer_min_charge._handle_winter_mode_changed(event)
        
        mock_notify.assert_called_once()
        summer_min_charge.async_write_ha_state.assert_called_once()


def test_handle_winter_mode_changed_winter_enabled(summer_min_charge, hass):
    """Test _handle_winter_mode_changed when winter mode is enabled."""
    event = MagicMock()
    event.data = {"enabled": True}
    
    # Mock async_write_ha_state to avoid HA integration issues
    summer_min_charge.async_write_ha_state = MagicMock()
    
    with patch.object(summer_min_charge, '_notify_dependents') as mock_notify:
        summer_min_charge._handle_winter_mode_changed(event)
        
        mock_notify.assert_not_called()
        summer_min_charge.async_write_ha_state.assert_called_once()


def test_handle_winter_mode_changed_no_data(summer_min_charge, hass):
    """Test _handle_winter_mode_changed with no event data."""
    event = MagicMock()
    event.data = {}
    
    # Mock async_write_ha_state to avoid HA integration issues
    summer_min_charge.async_write_ha_state = MagicMock()
    
    with patch.object(summer_min_charge, '_notify_dependents') as mock_notify:
        summer_min_charge._handle_winter_mode_changed(event)
        
        mock_notify.assert_called_once()
        summer_min_charge.async_write_ha_state.assert_called_once()


def test_device_info(summer_min_charge, entry):
    """Test device_info property."""
    device_info = summer_min_charge.device_info
    
    assert device_info["identifiers"] == {("maxxi_charge_connect", "test_entry")}
    assert device_info["name"] == "Test Entry"
    assert "manufacturer" in device_info
    assert "model" in device_info
