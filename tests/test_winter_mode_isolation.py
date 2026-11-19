"""Ensure winter mode changes remain isolated between configured CCUs.

These regression tests describe the desired multi-CCU behavior. They are
intentionally written before updating the production implementation (TDD).
"""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.maxxi_charge_connect.const import (
    CONF_WINTER_MODE,
    DOMAIN,
    WINTER_MODE_CHANGED_EVENT,
)
from custom_components.maxxi_charge_connect.winterbetrieb.winterbetrieb import Winterbetrieb


@pytest.fixture
def two_ccus():
    """Create two independent CCU entries sharing one Home Assistant instance."""
    hass = MagicMock()
    first = MagicMock()
    first.entry_id = "ccu_one"
    first.title = "CCU One"
    first.data = {}
    first.options = {CONF_WINTER_MODE: False}

    second = MagicMock()
    second.entry_id = "ccu_two"
    second.title = "CCU Two"
    second.data = {}
    second.options = {CONF_WINTER_MODE: True}

    hass.data = {
        DOMAIN: {
            first.entry_id: {CONF_WINTER_MODE: False},
            second.entry_id: {CONF_WINTER_MODE: True},
        }
    }
    return hass, first, second


@pytest.mark.asyncio
async def test_initial_winter_mode_is_read_from_own_ccu(two_ccus):
    """Each switch must initialize from its own CCU's saved winter mode."""
    hass, first, second = two_ccus
    first_switch = Winterbetrieb(first)
    second_switch = Winterbetrieb(second)
    first_switch.hass = hass
    second_switch.hass = hass

    with (
        patch.object(first_switch, "async_write_ha_state"),
        patch.object(second_switch, "async_write_ha_state"),
    ):
        await first_switch.async_added_to_hass()
        await second_switch.async_added_to_hass()

    assert first_switch.is_on is False
    assert second_switch.is_on is True


@pytest.mark.asyncio
async def test_switching_one_ccu_does_not_change_other_ccus_options(two_ccus):
    """Changing one CCU's winter mode must not change the other CCU's state."""
    hass, first, second = two_ccus
    first_switch = Winterbetrieb(first)
    second_switch = Winterbetrieb(second)
    first_switch.hass = hass
    second_switch.hass = hass

    with (
        patch.object(first_switch, "async_write_ha_state"),
        patch.object(second_switch, "async_write_ha_state"),
    ):
        await first_switch.async_added_to_hass()
        await second_switch.async_added_to_hass()
        await first_switch.async_turn_on()

    assert first_switch.is_on is True
    assert second_switch.is_on is True
    assert second.options[CONF_WINTER_MODE] is True
    hass.config_entries.async_update_entry.assert_called_once_with(first, options={CONF_WINTER_MODE: True})


@pytest.mark.asyncio
async def test_winter_mode_event_identifies_originating_ccu(two_ccus):
    """Winter mode events must include the entry ID for downstream filtering."""
    hass, first, _second = two_ccus
    winter_switch = Winterbetrieb(first)
    winter_switch.hass = hass

    with patch.object(winter_switch, "async_write_ha_state"):
        await winter_switch.async_turn_on()

    hass.bus.async_fire.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        {"entry_id": first.entry_id, "enabled": True},
    )
