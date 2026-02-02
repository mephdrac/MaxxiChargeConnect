"""Tests für die BatterySoc Entity der MaxxiChargeConnect Integration."""

from unittest.mock import MagicMock, AsyncMock, patch
from unittest.mock import call
from homeassistant.const import EntityCategory, PERCENTAGE

import pytest
from custom_components.maxxi_charge_connect.const import (
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
    DOMAIN
)

from custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge import WinterMaxCharge


@pytest.mark.asyncio
async def test_winter_max_charge__init():
    """ Konstruktortest von WinterMaxCharge
    """

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    winter_max_value = 61
    mock_config_entry.options.get.return_value = winter_max_value

    sensor = WinterMaxCharge(mock_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == mock_config_entry  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.CONFIG  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == PERCENTAGE  # pylint: disable=protected-access
    assert sensor.icon is None
    assert sensor._attr_unique_id == "1234abcd_winter_max_charge"  # pylint: disable=protected-access
    assert sensor.max_value == 100
    assert sensor.step == 1

    mock_config_entry.options.get.assert_has_calls([
        call(CONF_WINTER_MIN_CHARGE, DEFAULT_WINTER_MIN_CHARGE),
        call(CONF_WINTER_MAX_CHARGE, DEFAULT_WINTER_MAX_CHARGE),
    ])
    assert sensor._attr_native_value == winter_max_value  # pylint: disable=protected-access

    assert sensor._remove_listener is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_winter_max_charge__set_native_value():
    """Testet, ob die Methode set_native_value auch die Methode async_set_native_value aufruft"""

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_hass = MagicMock()

    captured_coro = None

    def fake_create_task(coro):
        nonlocal captured_coro
        captured_coro = coro

    value = 60

    sensor = WinterMaxCharge(mock_config_entry)
    sensor.hass = mock_hass
    sensor.hass.create_task = MagicMock(side_effect=fake_create_task)
    sensor.async_set_native_value = AsyncMock()

    sensor.set_native_value(value)  # zu testende Methode

    # Checks
    sensor.hass.create_task.assert_called_once()
    assert captured_coro is not None
    await captured_coro
    sensor.async_set_native_value.assert_awaited_once_with(value)


@patch(
    "custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge.async_get_min_soc_entity",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_winter_max_charge__async_set_native_value1(mock_async_get_min_soc_entity):
    """Testet die Methode, ob der Wert richtige gesetzt wird."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock(return_value=True)
    mock_state = MagicMock()

    new_value = 60
    cur_state = 20  # Aktueller Status der minSoc-Entität
    mock_state.state = cur_state

    sensor = WinterMaxCharge(mock_config_entry)
    mock_async_get_min_soc_entity.return_value = (mock_entity, mock_state)
    sensor.async_write_ha_state = MagicMock()
    sensor.hass = mock_hass
    sensor.hass.config_entries = MagicMock()
    sensor.hass.config_entries.async_update_entry = MagicMock()
    sensor.hass.data = {}

    await sensor.async_set_native_value(new_value)  # zu testende Methode

    # Checks
    assert sensor._attr_native_value == new_value  # pylint: disable=protected-access
    assert DOMAIN in sensor.hass.data
    assert sensor.hass.data[DOMAIN][CONF_WINTER_MAX_CHARGE] == new_value

    sensor.hass.config_entries.async_update_entry.assert_called_once()

    mock_async_get_min_soc_entity.assert_awaited_once_with(
        sensor.hass,
        sensor._entry.entry_id,  # pylint: disable=protected-access
    )
    mock_entity.set_change_limitation.assert_awaited_once_with(new_value, 5)   # pylint: disable=protected-access


@patch(
    "custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge.async_get_min_soc_entity",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_winter_max_charge__async_set_native_value2(mock_async_get_min_soc_entity):
    """Wert darf nicht gesetzt werden, wenn set_change_limitation False zurückgibt."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock(return_value=False)
    mock_state = MagicMock()

    new_value = 60
    cur_state = 20  # Aktueller Status der minSoc-Entität
    mock_state.state = cur_state

    sensor = WinterMaxCharge(mock_config_entry)
    mock_async_get_min_soc_entity.return_value = (mock_entity, mock_state)
    sensor.async_write_ha_state = MagicMock()
    sensor.hass = mock_hass
    sensor.hass.config_entries = MagicMock()
    sensor.hass.config_entries.async_update_entry = MagicMock()
    sensor.hass.data = {}

    await sensor.async_set_native_value(new_value)  # zu testende Methode

    # Checks
    assert sensor._attr_native_value != new_value  # pylint: disable=protected-access
    assert DOMAIN not in sensor.hass.data

    sensor.hass.config_entries.async_update_entry.assert_not_called()

    mock_async_get_min_soc_entity.assert_awaited_once_with(
        sensor.hass,
        sensor._entry.entry_id,  # pylint: disable=protected-access
    )
    mock_entity.set_change_limitation.assert_awaited_once_with(new_value, 5)   # pylint: disable=protected-access


@patch(
    "custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge.async_get_min_soc_entity",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_winter_max_charge__async_set_native_value3(mock_async_get_min_soc_entity):
    """min_soc_entity is None, State != None"""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock(return_value=True)
    mock_state = MagicMock()

    new_value = 60
    cur_state = 20  # Aktueller Status der minSoc-Entität
    mock_state.state = cur_state

    sensor = WinterMaxCharge(mock_config_entry)
    mock_async_get_min_soc_entity.return_value = (None, mock_state)
    sensor.async_write_ha_state = MagicMock()
    sensor.hass = mock_hass
    sensor.hass.config_entries = MagicMock()
    sensor.hass.config_entries.async_update_entry = MagicMock()
    sensor.hass.data = {}

    await sensor.async_set_native_value(new_value)  # zu testende Methode

    # Checks
    assert sensor._attr_native_value != new_value  # pylint: disable=protected-access
    assert DOMAIN not in sensor.hass.data

    sensor.hass.config_entries.async_update_entry.assert_not_called()

    mock_async_get_min_soc_entity.assert_awaited_once_with(
        sensor.hass,
        sensor._entry.entry_id,  # pylint: disable=protected-access
    )
    mock_entity.set_change_limitation.assert_not_awaited()   # pylint: disable=protected-access


@patch(
    "custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge.async_get_min_soc_entity",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_winter_max_charge__async_set_native_value4(mock_async_get_min_soc_entity):
    """min_soc_entity != None, State is None"""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock(return_value=True)

    new_value = 60

    sensor = WinterMaxCharge(mock_config_entry)
    mock_async_get_min_soc_entity.return_value = (mock_entity, None)
    sensor.async_write_ha_state = MagicMock()
    sensor.hass = mock_hass
    sensor.hass.config_entries = MagicMock()
    sensor.hass.config_entries.async_update_entry = MagicMock()
    sensor.hass.data = {}

    await sensor.async_set_native_value(new_value)  # zu testende Methode

    # Checks
    assert sensor._attr_native_value != new_value  # pylint: disable=protected-access
    assert DOMAIN not in sensor.hass.data

    sensor.hass.config_entries.async_update_entry.assert_not_called()

    mock_async_get_min_soc_entity.assert_awaited_once_with(
        sensor.hass,
        sensor._entry.entry_id,  # pylint: disable=protected-access
    )
    mock_entity.set_change_limitation.assert_not_awaited()   # pylint: disable=protected-access


@patch(
    "custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge.async_get_min_soc_entity",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_winter_max_charge__async_set_native_value5(mock_async_get_min_soc_entity):
    """min_soc_entity is None, State is None"""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"
    mock_config_entry.title = "Test Entry"

    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock(return_value=True)

    new_value = 60

    sensor = WinterMaxCharge(mock_config_entry)
    mock_async_get_min_soc_entity.return_value = (None, None)
    sensor.async_write_ha_state = MagicMock()
    sensor.hass = mock_hass
    sensor.hass.config_entries = MagicMock()
    sensor.hass.config_entries.async_update_entry = MagicMock()
    sensor.hass.data = {}

    await sensor.async_set_native_value(new_value)  # zu testende Methode

    # Checks
    assert sensor._attr_native_value != new_value  # pylint: disable=protected-access
    assert DOMAIN not in sensor.hass.data

    sensor.hass.config_entries.async_update_entry.assert_not_called()

    mock_async_get_min_soc_entity.assert_awaited_once_with(
        sensor.hass,
        sensor._entry.entry_id,  # pylint: disable=protected-access
    )
    mock_entity.set_change_limitation.assert_not_awaited()   # pylint: disable=protected-access
