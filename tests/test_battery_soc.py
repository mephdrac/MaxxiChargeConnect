"""Tests für die BatterySoc Entity der MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, PERCENTAGE
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import (
    DOMAIN,
    CONF_WINTER_MODE,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
    WINTER_MODE_CHANGED_EVENT
)
from custom_components.maxxi_charge_connect.devices.battery_soc import (
    BatterySoc,
)


@pytest.mark.asyncio
async def test_battery_soc__init():
    """ Initialisierung der BatterySoc Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoc(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == PERCENTAGE  # pylint: disable=protected-access
    assert sensor.icon == "mdi:battery-unknown"
    assert sensor._attr_unique_id == "1234abcd_battery_soc"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soc__async_added_to_hass():
    """Testet die async_added_to_hass Methode der BatterySoc Entity."""

    hass = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    dummy_config_entry.options = {}
    dummy_config_entry.data = {
        CONF_WEBHOOK_ID: "Webhook_ID"
    }

    # Wichtig: DOMAIN-Daten vorbereiten, sonst knallt BaseWebhookSensor
    hass.data = {
        DOMAIN: {
            dummy_config_entry.entry_id: {
                # Fake-Signale für BaseWebhookSensor
                WEBHOOK_SIGNAL_UPDATE: "update_signal",
                WEBHOOK_SIGNAL_STATE: "stale_signal",
            },
            CONF_WINTER_MODE: False,
        }
    }

    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass

    await sensor.async_added_to_hass()

    hass.bus.async_listen.assert_called_once_with(
        WINTER_MODE_CHANGED_EVENT,
        sensor._handle_winter_mode_changed,  # pylint: disable=protected-access
    )


@pytest.mark.asyncio
async def test_battery_soc__device_info():
    """ Testet die device_info Eigenschaft der BatterySoc Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoc(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soc__handle_update_alles_ok():
    """ _handle_update Methode der BatterySoc Entity testen, wenn alle Bedingungen erfüllt sind."""

    hass = MagicMock()
    hass.async_add_job = AsyncMock()
    hass.data = {
        DOMAIN: {
            CONF_WINTER_MODE: False,
        }
    }

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    soc = 37.623

    data = {
        "SOC": soc
    }

    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    with patch(
        "custom_components.maxxi_charge_connect.devices.battery_soc.BatterySoc.async_write_ha_state",
        new_callable=MagicMock,
    ) as mock_write_ha_state:

        await sensor.handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == soc  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soc__icon_0_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 0 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 0  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-outline"


@pytest.mark.asyncio
async def test_battery_soc__icon_18_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 18 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 18  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-20"


@pytest.mark.asyncio
async def test_battery_soc__icon_38_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 38 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 38  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-40"


@pytest.mark.asyncio
async def test_battery_soc__icon_100_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 100 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 100  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery"
