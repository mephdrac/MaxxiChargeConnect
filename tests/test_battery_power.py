"""Tests für die BatteryPower Sensor Entity der MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_power import (
    BatteryPower,
)


@pytest.mark.asyncio
async def test_battery_power_init():
    """ Initialisierung der BatteryPower Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPower(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT  # pylint: disable=protected-access
    assert sensor.icon == "mdi:battery-charging-outline"
    assert sensor._attr_unique_id == "1234abcd_battery_power"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access

@pytest.mark.asyncio
async def test_battery_power_device_info():
    """ Testet die device_info Eigenschaft der BatteryPower Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPower(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_power__handle_update_alles_ok():
    """ _handle_update Methode der BatteryPower Entity testen, wenn alle Bedingungen erfüllt sind."""
    # is_pccu_ok(ccu) == true
    # is_power_total_ok(pv_power, batteries) == true
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pccu = 37.623
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPower(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_power.BatteryPower.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor.handle_update(data)  # pylint: disable=protected-access
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == round(pv_power - pccu, 3)  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power__handle_update_pccu_nicht_ok():
    """ _handle_update Methode der BatteryPower Entity testen, wenn die PCCU Bedingung nicht erfüllt ist."""
    # is_pccu_ok(ccu) == false
    # is_power_total_ok(pv_power, batteries) == true

    dummy_config_entry = MagicMock()

    pccu = 36500
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPower(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "BatteryPower.async_write_ha_state",
                new_callable=MagicMock
            ) as mock_write_ha_state1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_pccu_ok",
                return_value=False
            ) as mock_is_pccu_ok1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_power_total_ok",
                return_value=True
            ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_not_called()
        mock_is_pccu_ok1.assert_called_once()
        mock_write_ha_state1.assert_not_called()

        args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

        assert args[0] == pccu
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power__handle_update_alles_nicht_ok():
    """ _handle_update Methode der BatteryPower Entity testen, wenn keine der Bedingungen erfüllt ist."""
    # is_pccu_ok(ccu) == false
    # is_power_total_ok(pv_power, batteries) == false

    dummy_config_entry = MagicMock()

    pccu = 36500
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPower(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "BatteryPower.async_write_ha_state",
                new_callable=MagicMock
            ) as mock_write_ha_state1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_pccu_ok",
                return_value=False
            ) as mock_is_pccu_ok1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_power_total_ok",
                return_value=False
            ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_not_called()
        mock_is_pccu_ok1.assert_called_once()
        mock_write_ha_state1.assert_not_called()

        args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

        assert args[0] == pccu
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power__handle_update_power_total_nicht_ok():
    """ _handle_update Methode der BatteryPower Entity testen, wenn die Power Total Bedingung nicht erfüllt ist."""
    # is_pccu_ok(ccu) == true
    # is_power_total_ok(pv_power, batteries) == false

    dummy_config_entry = MagicMock()

    pccu = 45.345
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPower(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "BatteryPower.async_write_ha_state",
                new_callable=MagicMock
            ) as mock_write_ha_state1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_pccu_ok",
                return_value=True
            ) as mock_is_pccu_ok1,

            patch(
                "custom_components.maxxi_charge_connect.devices.battery_power."
                "is_power_total_ok",
                return_value=False
            ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_called_once()
        mock_is_pccu_ok1.assert_called_once()
        mock_write_ha_state1.assert_not_called()

        args1, kwargs1 = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable
        args2, kwargs2 = mock_is_power_ok1.call_args  # pylint: disable=unused-variable
        assert args1[0] == pccu
        assert args2[0] == pv_power
        assert args2[1] == [{"batteryCapacity": 1187.339966}]
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access
