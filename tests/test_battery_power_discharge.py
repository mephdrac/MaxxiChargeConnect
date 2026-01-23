"""Tests für die BatteryPowerDischarge Sensor Entität."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_power_discharge import (
    BatteryPowerDischarge,
)


@pytest.mark.asyncio
async def test_battery_power_discharge__init():
    """Testet die Initialisierung der BatteryPowerDischarge Entität."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPowerDischarge(dummy_config_entry)
    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT  # pylint: disable=protected-access
    assert sensor.icon == "mdi:battery-minus-variant"
    assert sensor._attr_unique_id == "1234abcd_battery_power_discharge"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
@patch("custom_components.maxxi_charge_connect.devices.battery_power_discharge.async_dispatcher_connect")
async def test_battery_power_discharge__async_added_to_hass(mock_dispatcher_connect):
    """Testet die async_added_to_hass Methode der BatteryPowerDischarge Entität."""

    mock_dispatcher_connect.return_value = lambda: None

    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    dummy_config_entry.options = {}

    dummy_config_entry.data = {
        CONF_WEBHOOK_ID: "Webhook_ID"
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)
    sensor.hass = hass

    await sensor.async_added_to_hass()

    mock_dispatcher_connect.assert_called_once()
    args, kwargs = mock_dispatcher_connect.call_args  # pylint: disable=unused-variable

    assert args[0] is hass
    assert args[1] == f"{DOMAIN}_{dummy_config_entry.data[CONF_WEBHOOK_ID]}_update_sensor"
    assert args[2].__name__ == "_handle_update"


@pytest.mark.asyncio
async def test_battery_power_discharge__device_info():
    """Testet die device_info Eigenschaft der BatteryPowerDischarge Entität."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPowerDischarge(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_alles_ok_power_groesser_0():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn alles ok ist und die Batterieleistung größer 0 ist.
    """

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
    sensor = BatteryPowerDischarge(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_power_discharge.BatteryPowerDischarge.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)  # pylint: disable=protected-access
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == 0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_alles_ok_aber_batterieleistung_kleiner_0():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn alles ok ist aber die Batterieleistung kleiner 0 ist."""

    # is_pccu_ok(ccu) == true
    # is_power_total_ok(pv_power, batteries) == true
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pccu = 37.623
    pv_power = 10

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_power_discharge.BatteryPowerDischarge.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)  # pylint: disable=protected-access
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == round(pv_power - pccu, 3) * -1  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_pccu_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn PCCU nicht ok ist."""
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

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "BatteryPowerDischarge.async_write_ha_state",
            new_callable=MagicMock,
        ) as mock_write_ha_state1,
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=False,
        ) as mock_is_pccu_ok1,
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=True,
        ) as mock_is_power_ok1,
    ):
        await sensor1._handle_update(data)  # pylint: disable=protected-access

    mock_is_power_ok1.assert_not_called()
    mock_is_pccu_ok1.assert_called_once()
    mock_write_ha_state1.assert_not_called()

    args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

    assert args[0] == pccu
    assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_alles_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn weder PCCU noch Leistung ok sind."""
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

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "BatteryPowerDischarge.async_write_ha_state",
            new_callable=MagicMock
        ) as mock_write_ha_state1,

        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=False
        ) as mock_is_pccu_ok1,

        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=False
        ) as mock_is_power_ok1
    ):
        await sensor1._handle_update(data)  # pylint: disable=protected-access

    mock_is_power_ok1.assert_not_called()
    mock_is_pccu_ok1.assert_called_once()
    mock_write_ha_state1.assert_not_called()

    args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

    assert args[0] == pccu
    assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_power_total_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn die Leistung nicht ok ist."""

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

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (

        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "BatteryPowerDischarge.async_write_ha_state",
            new_callable=MagicMock
        ) as mock_write_ha_state1,

        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=True
        ) as mock_is_pccu_ok1,

        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=False
        ) as mock_is_power_ok1
    ):

        await sensor1._handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_called_once()
        mock_is_pccu_ok1.assert_called_once()
        mock_write_ha_state1.assert_not_called()

        args1, kwargs1 = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable
        args2, kwargs2 = mock_is_power_ok1.call_args  # pylint: disable=unused-variable
        assert args1[0] == pccu
        assert args2[0] == pv_power
        assert args2[1] == [{"batteryCapacity": 1187.339966}]
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access
