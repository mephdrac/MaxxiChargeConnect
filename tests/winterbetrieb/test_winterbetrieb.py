"""Tests für Winterbetrieb SwitchEntity."""

from unittest.mock import MagicMock, patch
import pytest

from custom_components.maxxi_charge_connect.winterbetrieb.winterbetrieb import (
    Winterbetrieb,
)
from custom_components.maxxi_charge_connect.const import (
    CONF_WINTER_MODE,
    DOMAIN,
    WINTER_MODE_CHANGED_EVENT,
)


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"
    entry.options = {CONF_WINTER_MODE: False}
    return entry


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {CONF_WINTER_MODE: False}}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def winterbetrieb_entity(entry, hass):
    """Create Winterbetrieb instance for testing."""
    entity = Winterbetrieb(entry)
    entity.hass = hass
    return entity


def test_initialization(winterbetrieb_entity, entry):
    """Test that Winterbetrieb initializes correctly."""
    assert winterbetrieb_entity._entry == entry
    assert winterbetrieb_entity._attr_unique_id == "test_entry_winterbetrieb"
    assert winterbetrieb_entity._attr_entity_category.name == "CONFIG"
    assert winterbetrieb_entity._attr_should_poll is False
    assert winterbetrieb_entity._state is False


def test_is_on(winterbetrieb_entity):
    """Test is_on property."""
    winterbetrieb_entity._state = True
    assert winterbetrieb_entity.is_on is True
    
    winterbetrieb_entity._state = False
    assert winterbetrieb_entity.is_on is False
    
    winterbetrieb_entity._state = None
    assert winterbetrieb_entity.is_on is False


def test_turn_on(winterbetrieb_entity):
    """Test turn_on method."""
    with patch.object(winterbetrieb_entity, 'async_turn_on', new_callable=MagicMock) as mock_async_on:
        mock_async_on.return_value = None
        winterbetrieb_entity.turn_on()
        mock_async_on.assert_called_once()


def test_turn_off(winterbetrieb_entity):
    """Test turn_off method."""
    with patch.object(winterbetrieb_entity, 'async_turn_off', new_callable=MagicMock) as mock_async_off:
        mock_async_off.return_value = None
        winterbetrieb_entity.turn_off()
        mock_async_off.assert_called_once()


@pytest.mark.asyncio
async def test_async_turn_on(winterbetrieb_entity, hass, entry):
    """Test async_turn_on method."""
    # Mock async_write_ha_state to avoid HA integration issues
    winterbetrieb_entity.async_write_ha_state = MagicMock()
    
    await winterbetrieb_entity.async_turn_on()
    
    assert winterbetrieb_entity._state is True
    assert hass.data[DOMAIN][CONF_WINTER_MODE] is True
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={
            **entry.options,
            CONF_WINTER_MODE: True,
        },
    )
    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"enabled": True}
    )
    winterbetrieb_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_turn_off(winterbetrieb_entity, hass, entry):
    """Test async_turn_off method."""
    # Mock async_write_ha_state to avoid HA integration issues
    winterbetrieb_entity.async_write_ha_state = MagicMock()
    
    await winterbetrieb_entity.async_turn_off()
    
    assert winterbetrieb_entity._state is False
    assert hass.data[DOMAIN][CONF_WINTER_MODE] is False
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={
            **entry.options,
            CONF_WINTER_MODE: False,
        },
    )
    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"enabled": False}
    )
    winterbetrieb_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass(winterbetrieb_entity, hass):
    """Test async_added_to_hass method."""
    # Mock async_write_ha_state to avoid HA integration issues
    winterbetrieb_entity.async_write_ha_state = MagicMock()
    
    hass.data[DOMAIN][CONF_WINTER_MODE] = True
    
    await winterbetrieb_entity.async_added_to_hass()
    
    assert winterbetrieb_entity._state is True
    winterbetrieb_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_added_to_hass_missing_data(winterbetrieb_entity, hass):
    """Test async_added_to_hass with missing data."""
    # Mock async_write_ha_state to avoid HA integration issues
    winterbetrieb_entity.async_write_ha_state = MagicMock()
    
    hass.data[DOMAIN] = {}  # CONF_WINTER_MODE not present
    
    await winterbetrieb_entity.async_added_to_hass()
    
    assert winterbetrieb_entity._state is False
    winterbetrieb_entity.async_write_ha_state.assert_called_once()


def test_notify_dependents(winterbetrieb_entity, hass):
    """Test _notify_dependents method."""
    winterbetrieb_entity._state = True
    
    winterbetrieb_entity._notify_dependents()
    
    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"enabled": True}
    )


def test_notify_dependents_false(winterbetrieb_entity, hass):
    """Test _notify_dependents method with False state."""
    winterbetrieb_entity._state = False
    
    winterbetrieb_entity._notify_dependents()
    
    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"enabled": False}
    )


def test_device_info(winterbetrieb_entity, entry):
    """Test device_info property."""
    device_info = winterbetrieb_entity.device_info
    
    assert device_info["identifiers"] == {("maxxi_charge_connect", "test_entry")}
    assert device_info["name"] == "Test Entry"
    assert "manufacturer" in device_info
    assert "model" in device_info


@pytest.mark.asyncio
async def test_save_state(winterbetrieb_entity, hass, entry):
    """Test _save_state method."""
    # Mock async_write_ha_state to avoid HA integration issues
    winterbetrieb_entity.async_write_ha_state = MagicMock()
    
    await winterbetrieb_entity._save_state(True)
    
    assert winterbetrieb_entity._state is True
    assert hass.data[DOMAIN][CONF_WINTER_MODE] is True
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        options={
            **entry.options,
            CONF_WINTER_MODE: True,
        },
    )
    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"enabled": True}
    )
    winterbetrieb_entity.async_write_ha_state.assert_called_once()
