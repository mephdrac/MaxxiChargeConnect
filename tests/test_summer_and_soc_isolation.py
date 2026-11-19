"""Specify independent summer settings, control events, and SOC logic per CCU.

These regression tests are written before the corresponding production changes.
They intentionally distinguish the two config entries on one Home Assistant instance.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS

from custom_components.maxxi_charge_connect.const import (
    CONF_SUMMER_MIN_CHARGE,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    CONF_WINTER_MODE,
    DOMAIN,
    EVENT_SUMMER_MIN_CHARGE_CHANGED,
)
from custom_components.maxxi_charge_connect.devices.battery_soc import BatterySoc
from custom_components.maxxi_charge_connect.http_post.number_config_entity import NumberConfigEntity
from custom_components.maxxi_charge_connect.winterbetrieb.summer_min_charge import SummerMinCharge


@pytest.fixture
def two_ccus():
    """Provide one HA instance with independently configured CCU entries."""
    hass = MagicMock()
    first = SimpleNamespace(
        entry_id="ccu_one",
        title="CCU One",
        data={CONF_IP_ADDRESS: "192.168.1.10"},
        options={CONF_WINTER_MODE: True, CONF_SUMMER_MIN_CHARGE: 10},
    )
    second = SimpleNamespace(
        entry_id="ccu_two",
        title="CCU Two",
        data={CONF_IP_ADDRESS: "192.168.1.20"},
        options={CONF_WINTER_MODE: False, CONF_SUMMER_MIN_CHARGE: 25},
    )
    hass.data = {
        DOMAIN: {
            first.entry_id: {
                CONF_WINTER_MODE: True,
                CONF_SUMMER_MIN_CHARGE: 10,
                CONF_WINTER_MIN_CHARGE: 20,
                CONF_WINTER_MAX_CHARGE: 60,
                "coordinator": MagicMock(entry=first, data={"minSOC": 20}),
            },
            second.entry_id: {
                CONF_WINTER_MODE: False,
                CONF_SUMMER_MIN_CHARGE: 25,
                CONF_WINTER_MIN_CHARGE: 30,
                CONF_WINTER_MAX_CHARGE: 70,
                "coordinator": MagicMock(entry=second, data={"minSOC": 30}),
            },
        }
    }
    return hass, first, second


def summer_entity(hass, entry):
    """Construct a summer control without registering a real HA platform."""
    entity = SummerMinCharge(entry)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    return entity


def number_entity(hass, entry):
    """Construct a minSOC device control using its existing mock coordinator."""
    entity = NumberConfigEntity(
        hass,
        entry,
        "min_soc",
        "minSOC",
        "minSOC",
        0,
        100,
        1,
        "%",
        depends_on_winter_mode=True,
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    entity.set_native_value = MagicMock()
    return entity


def battery_sensor(hass, entry):
    """Build an SOC sensor with its real class but mocked HA platform."""
    entity = BatterySoc(entry)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    return entity


def test_summer_availability_uses_own_winter_mode(two_ccus):
    """Only the CCU without winter mode exposes the summer setting."""
    hass, first, second = two_ccus
    assert summer_entity(hass, first).available is False
    assert summer_entity(hass, second).available is True


@pytest.mark.asyncio
async def test_summer_setting_persists_only_to_its_entry(two_ccus):
    """Changing CCU one's summer threshold must not overwrite CCU two's."""
    hass, first, second = two_ccus
    entity = summer_entity(hass, first)

    await entity.async_set_native_value(15)

    assert hass.data[DOMAIN][first.entry_id][CONF_SUMMER_MIN_CHARGE] == 15
    assert hass.data[DOMAIN][second.entry_id][CONF_SUMMER_MIN_CHARGE] == 25
    hass.config_entries.async_update_entry.assert_called_once()
    args, kwargs = hass.config_entries.async_update_entry.call_args
    assert args[0] is first
    assert kwargs["options"][CONF_SUMMER_MIN_CHARGE] == 15


def test_summer_change_event_carries_originating_entry(two_ccus):
    """Summer-change notifications identify the originating CCU."""
    hass, first, _second = two_ccus
    entity = summer_entity(hass, first)

    entity._notify_dependents()

    hass.bus.async_fire.assert_called_once_with(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"entry_id": first.entry_id, "value": 10},
    )


def test_foreign_winter_event_does_not_refresh_summer_entity(two_ccus):
    """A different CCU's winter mode must not refresh or notify this entity."""
    hass, first, second = two_ccus
    entity = summer_entity(hass, second)

    entity._handle_winter_mode_changed(SimpleNamespace(data={"entry_id": first.entry_id, "enabled": False}))

    entity.async_write_ha_state.assert_not_called()
    hass.bus.async_fire.assert_not_called()


def test_own_winter_event_reactivates_own_summer_limit(two_ccus):
    """Leaving winter mode sends only this CCU's summer threshold."""
    hass, _first, second = two_ccus
    entity = summer_entity(hass, second)

    entity._handle_winter_mode_changed(SimpleNamespace(data={"entry_id": second.entry_id, "enabled": False}))

    entity.async_write_ha_state.assert_called_once()
    hass.bus.async_fire.assert_called_once_with(
        EVENT_SUMMER_MIN_CHARGE_CHANGED,
        {"entry_id": second.entry_id, "value": 25},
    )


def test_device_control_ignores_foreign_summer_event(two_ccus):
    """Another CCU's summer threshold must not be sent via HTTP to this CCU."""
    hass, first, second = two_ccus
    entity = number_entity(hass, second)

    entity._handle_summer_charge_changed(SimpleNamespace(data={"entry_id": first.entry_id, "value": 15}))

    entity.set_native_value.assert_not_called()
    entity.async_write_ha_state.assert_not_called()


def test_device_control_accepts_own_summer_event(two_ccus):
    """A valid summer event for this CCU reaches its minSOC control."""
    hass, _first, second = two_ccus
    entity = number_entity(hass, second)

    entity._handle_summer_charge_changed(SimpleNamespace(data={"entry_id": second.entry_id, "value": 25}))

    entity.set_native_value.assert_called_once_with(25.0)


def test_device_control_ignores_foreign_winter_event(two_ccus):
    """Another CCU's winter event must not refresh this number entity."""
    hass, first, second = two_ccus
    entity = number_entity(hass, second)

    entity._handle_winter_mode_changed(SimpleNamespace(data={"entry_id": first.entry_id, "enabled": True}))

    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_battery_upper_limit_uses_own_ccu_threshold(two_ccus):
    """SOC upper-limit checks use the battery's CCU-specific thresholds."""
    hass, _first, second = two_ccus
    sensor = battery_sensor(hass, second)

    assert await sensor._check_upper_limit_reached(65, 40) is False
    assert await sensor._check_upper_limit_reached(75, 40) is True


@pytest.mark.asyncio
async def test_battery_lower_limit_uses_own_ccu_threshold(two_ccus):
    """SOC lower-limit checks use the battery's CCU-specific thresholds."""
    hass, _first, second = two_ccus
    sensor = battery_sensor(hass, second)

    assert await sensor._check_lower_limit_reached(25, 40) is True
    assert await sensor._check_lower_limit_reached(35, 40) is False


@pytest.mark.asyncio
async def test_battery_update_uses_own_winter_mode(two_ccus):
    """CCU two must not run winter SOC logic when only CCU one is in winter mode."""
    hass, _first, second = two_ccus
    sensor = battery_sensor(hass, second)

    with patch.object(sensor, "_do_wintermode", new_callable=AsyncMock) as winter_logic:
        await sensor.handle_update({"SOC": 45})

    winter_logic.assert_not_awaited()
    assert sensor.native_value == 45
