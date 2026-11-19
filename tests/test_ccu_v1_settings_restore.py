"""Regression tests for restoring per-CCU operating settings at startup.

The tests stop setup at the first coordinator refresh, after the settings
have been loaded but before webhooks, platform setup, or network activity.
"""

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.maxxi_charge_connect.connection import ccu_v1_connection
from custom_components.maxxi_charge_connect.const import (
    CONF_SUMMER_MIN_CHARGE,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MODE,
    DEFAULT_SUMMER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MODE,
    DOMAIN,
)


class _StopAfterSettingsLoaded(Exception):
    """Interrupt setup at the first coordinator refresh for unit isolation."""


def _get_connection_class():
    """Locate the V1 implementation without depending on its class name."""
    matches = [
        cls
        for _name, cls in inspect.getmembers(ccu_v1_connection, inspect.isclass)
        if cls.__module__ == ccu_v1_connection.__name__ and "async_setup_entry" in cls.__dict__
    ]
    assert len(matches) == 1, "Expected one V1 connection setup implementation"
    return matches[0]


async def _initialize_until_first_refresh(hass, entry):
    """Exercise real startup initialization without network side effects."""
    connection = MagicMock()
    connection.hass = hass
    connection.entry = entry
    coordinator = SimpleNamespace(async_config_entry_first_refresh=AsyncMock(side_effect=_StopAfterSettingsLoaded))
    with patch.object(ccu_v1_connection, "MaxxiDataUpdateCoordinator", return_value=coordinator):
        with pytest.raises(_StopAfterSettingsLoaded):
            await _get_connection_class().async_setup_entry(connection)


def _entry(entry_id, *, winter, summer_min, winter_min, winter_max):
    """Provide persisted options with deliberately different CCU settings."""
    return SimpleNamespace(
        entry_id=entry_id,
        options={
            CONF_WINTER_MODE: winter,
            CONF_SUMMER_MIN_CHARGE: summer_min,
            CONF_WINTER_MIN_CHARGE: winter_min,
            CONF_WINTER_MAX_CHARGE: winter_max,
        },
    )


@pytest.mark.asyncio
async def test_startup_restores_all_four_settings_for_two_independent_ccus():
    """Both CCUs must recover their own saved values before their first update."""
    hass = MagicMock()
    hass.data = {}
    first = _entry("ccu_one", winter=True, summer_min=12, winter_min=28, winter_max=72)
    second = _entry("ccu_two", winter=False, summer_min=17, winter_min=35, winter_max=85)

    await _initialize_until_first_refresh(hass, first)
    await _initialize_until_first_refresh(hass, second)

    for entry in (first, second):
        stored = hass.data[DOMAIN][entry.entry_id]
        for key in (
            CONF_WINTER_MODE,
            CONF_SUMMER_MIN_CHARGE,
            CONF_WINTER_MIN_CHARGE,
            CONF_WINTER_MAX_CHARGE,
        ):
            assert stored[key] == entry.options[key], f"{entry.entry_id} did not restore {key} from its own options"

    assert hass.data[DOMAIN][first.entry_id] is not hass.data[DOMAIN][second.entry_id]
    for key in (
        CONF_WINTER_MODE,
        CONF_SUMMER_MIN_CHARGE,
        CONF_WINTER_MIN_CHARGE,
        CONF_WINTER_MAX_CHARGE,
    ):
        assert key not in hass.data[DOMAIN], f"{key} leaked into global integration state"


@pytest.mark.asyncio
async def test_startup_uses_defaults_when_operating_options_are_absent():
    """New configurations should initialize all four operating settings."""
    hass = MagicMock()
    hass.data = {}
    entry = SimpleNamespace(entry_id="ccu_default", options={})

    await _initialize_until_first_refresh(hass, entry)

    settings = hass.data[DOMAIN][entry.entry_id]
    assert settings[CONF_WINTER_MODE] == DEFAULT_WINTER_MODE
    assert settings[CONF_SUMMER_MIN_CHARGE] == DEFAULT_SUMMER_MIN_CHARGE
    assert settings[CONF_WINTER_MIN_CHARGE] == DEFAULT_WINTER_MIN_CHARGE
    assert settings[CONF_WINTER_MAX_CHARGE] == DEFAULT_WINTER_MAX_CHARGE
