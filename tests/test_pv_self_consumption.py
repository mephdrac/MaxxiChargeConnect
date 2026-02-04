"""Testet die Initialisierung und Attribute des `PvSelfConsumption` Sensors."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import UnitOfPower
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.devices.pv_self_consumption import (
    PvSelfConsumption,
)


@pytest.mark.asyncio
async def test_pv_self_consumption__init():
    """Testet die Initialisierung der PvSelfConsumption Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = PvSelfConsumption(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT  # pylint: disable=protected-access
    assert sensor.icon == "mdi:solar-power-variant"
    assert sensor._attr_unique_id == "1234abcd_pv_consumption"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_pv_self_consumption__device_info():
    """ device_info Property der PvSelfConsumption Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = PvSelfConsumption(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_alles_ok():
    """ _handle_update Methode der PvSelfConsumption Entity testen, wenn alle Bedingungen erfüllt sind."""

    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pr = 37.623
    pv_power = 218

    data = {
        "Pr": pr,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = PvSelfConsumption(dummy_config_entry)

    await sensor.handle_update(data)
    assert sensor._attr_native_value == round(pv_power - max(-pr, 0), 2)  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_pr_nicht_ok():
    """ _handle_update Methode der PvSelfConsumption Entity testen, wenn PR nicht ok ist."""

    # is_pr_ok(pr) == false
    # is_power_total_ok(pv_power, batteries) == true

    dummy_config_entry = MagicMock()

    pr = 35
    pv_power = 218

    data = {
        "Pr": pr,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = PvSelfConsumption(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices.pv_self_consumption."
                "is_pr_ok",
                return_value=False
            ) as mock_is_pr_ok1,

            patch(
                "custom_components.maxxi_charge_connect.devices.pv_self_consumption."
                "is_power_total_ok",
                return_value=True
            ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)

        mock_is_power_ok1.assert_called_once()
        mock_is_pr_ok1.assert_called_once()

        args, kwargs = mock_is_pr_ok1.call_args  # pylint: disable=unused-variable

        assert args[0] == pr
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_power_nicht_ok():
    """ _handle_update Methode der PvSelfConsumption Entity testen, wenn PV-Leistung nicht ok ist."""
    # is_pr_ok(pr) == true
    # is_power_total_ok(pv_power, batteries) == false

    dummy_config_entry = MagicMock()

    pr = 35
    pv_power = 218

    data = {
        "Pr": pr,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = PvSelfConsumption(dummy_config_entry)

    with (
            patch(
                "custom_components.maxxi_charge_connect.devices."
                "pv_self_consumption.is_pr_ok",
                return_value=True
            ) as mock_is_pr_ok1,

            patch(
                "custom_components.maxxi_charge_connect.devices."
                "pv_self_consumption.is_power_total_ok",
                return_value=False
            ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)

        mock_is_power_ok1.assert_called_once()
        mock_is_pr_ok1.assert_not_called()

        args, kwargs = mock_is_power_ok1.call_args  # pylint: disable=unused-variable

        assert args[0] == float(data.get("PV_power_total"))
        assert args[1] == data.get("batteriesInfo", [])
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access
