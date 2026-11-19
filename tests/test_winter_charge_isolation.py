"""Verify that winter charge controls remain isolated between CCU entries.

These tests describe the desired multi-CCU behavior. They intentionally fail
against the previous global-state and unscoped-event implementation.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.maxxi_charge_connect.const import (
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MODE,
    DOMAIN,
    EVENT_WINTER_MAX_CHARGE_CHANGED,
)
from custom_components.maxxi_charge_connect.winterbetrieb.winter_max_charge import WinterMaxCharge
from custom_components.maxxi_charge_connect.winterbetrieb.winter_min_charge import WinterMinCharge


@pytest.fixture
def two_ccus():
    """Provide independent entries and a shared Home Assistant mock."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "ccu_one": {
                CONF_WINTER_MODE: True,
                CONF_WINTER_MIN_CHARGE: 20,
                CONF_WINTER_MAX_CHARGE: 60,
            },
            "ccu_two": {
                CONF_WINTER_MODE: False,
                CONF_WINTER_MIN_CHARGE: 30,
                CONF_WINTER_MAX_CHARGE: 70,
            },
        }
    }
    first = SimpleNamespace(
        entry_id="ccu_one",
        options={CONF_WINTER_MODE: True, CONF_WINTER_MIN_CHARGE: 20, CONF_WINTER_MAX_CHARGE: 60},
        data={},
        title="CCU One",
    )
    second = SimpleNamespace(
        entry_id="ccu_two",
        options={CONF_WINTER_MODE: False, CONF_WINTER_MIN_CHARGE: 30, CONF_WINTER_MAX_CHARGE: 70},
        data={},
        title="CCU Two",
    )
    return hass, first, second


def make_entity(entity_class, hass, entry):
    """Attach a control to the shared mocked HA instance without a platform."""
    entity = entity_class(entry)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    return entity


@pytest.mark.parametrize("entity_class", [WinterMinCharge, WinterMaxCharge])
def test_winter_control_availability_depends_on_own_ccu(two_ccus, entity_class):
    """Only the CCU in winter mode exposes its own winter settings."""
    hass, first, second = two_ccus
    first_control = make_entity(entity_class, hass, first)
    second_control = make_entity(entity_class, hass, second)

    assert first_control.available is True
    assert second_control.available is False


@pytest.mark.parametrize(
    ("entity_class", "setting", "value", "module_name"),
    [
        (WinterMinCharge, CONF_WINTER_MIN_CHARGE, 25, "winter_min_charge"),
        (WinterMaxCharge, CONF_WINTER_MAX_CHARGE, 65, "winter_max_charge"),
    ],
)
@pytest.mark.asyncio
async def test_updating_limit_only_changes_own_ccu(two_ccus, entity_class, setting, value, module_name):
    """Persist an accepted limit exclusively for the originating config entry."""
    hass, first, second = two_ccus
    entity = make_entity(entity_class, hass, first)
    control = MagicMock()
    control.set_change_limitation = AsyncMock(return_value=True)

    with patch(
        f"custom_components.maxxi_charge_connect.winterbetrieb.{module_name}.async_get_min_soc_entity",
        new=AsyncMock(return_value=(control, 0)),
    ):
        await entity.async_set_native_value(value)

    assert hass.data[DOMAIN][first.entry_id][setting] == value
    assert hass.data[DOMAIN][second.entry_id][setting] == second.options[setting]
    hass.config_entries.async_update_entry.assert_called_once()
    call_args, call_kwargs = hass.config_entries.async_update_entry.call_args
    assert call_args[0] is first
    assert call_kwargs["options"][setting] == value


def test_max_charge_change_event_identifies_its_ccu(two_ccus):
    """Include the originating entry in the maximum-charge change event."""
    hass, first, _second = two_ccus
    maximum = make_entity(WinterMaxCharge, hass, first)

    maximum._notify_dependents(65)

    hass.bus.async_fire.assert_called_once_with(
        EVENT_WINTER_MAX_CHARGE_CHANGED,
        {"entry_id": first.entry_id, "value": 65},
    )


@pytest.mark.asyncio
async def test_other_ccu_maximum_event_cannot_clamp_minimum(two_ccus):
    """Ignore a maximum-change event belonging to another CCU."""
    hass, first, second = two_ccus
    minimum = make_entity(WinterMinCharge, hass, second)
    minimum.async_set_native_value = AsyncMock()
    original_maximum = minimum.native_max_value
    foreign_event = SimpleNamespace(data={"entry_id": first.entry_id, "value": 10})

    await minimum._handle_winter_max_charge_changed(foreign_event)

    minimum.async_set_native_value.assert_not_awaited()
    assert minimum.native_max_value == original_maximum
    minimum.async_write_ha_state.assert_not_called()


@pytest.mark.parametrize("entity_class", [WinterMinCharge, WinterMaxCharge])
def test_other_ccu_winter_mode_event_does_not_update_state(two_ccus, entity_class):
    """Ignore a winter-mode event if the entry ID belongs to another CCU."""
    hass, first, second = two_ccus
    control = make_entity(entity_class, hass, second)
    foreign_event = SimpleNamespace(data={"entry_id": first.entry_id, "enabled": True})

    control._handle_winter_mode_changed(foreign_event)

    control.async_write_ha_state.assert_not_called()
