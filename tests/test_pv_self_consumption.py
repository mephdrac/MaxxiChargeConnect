from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.components.sensor import (
    SensorDeviceClass,    
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.pv_self_consumption import (
    PvSelfConsumption,
)

@pytest.mark.asyncio
async def test_pv_self_consumption__init(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    
    sensor = PvSelfConsumption(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_device_class == SensorDeviceClass.POWER
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    assert sensor.icon == "mdi:solar-power-variant"
    assert sensor._attr_unique_id == "1234abcd_pv_consumption"
    assert sensor._attr_native_value is None
    
@pytest.mark.asyncio
@patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.async_dispatcher_connect")
async def test_pv_self_consumption__async_added_to_hass(mock_dispatcher_connect):
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

    sensor = PvSelfConsumption(dummy_config_entry)
    sensor.hass = hass
        
    await sensor.async_added_to_hass()

    mock_dispatcher_connect.assert_called_once()
    args, kwargs = mock_dispatcher_connect.call_args

    assert args[0] is hass
    assert args[1] == f"{DOMAIN}_{dummy_config_entry.data[CONF_WEBHOOK_ID]}_update_sensor"
    assert args[2].__name__ == "_handle_update"


@pytest.mark.asyncio
async def test_pv_self_consumption__device_info(caplog):

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = PvSelfConsumption(dummy_config_entry)
    
    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_alles_ok(caplog):
    
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

    with patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.PvSelfConsumption.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == pv_power - max(-pr, 0)


@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_pr_nicht_ok(caplog):
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

    with patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.PvSelfConsumption.async_write_ha_state", 
               new_callable=MagicMock
               ) as mock_write_ha_state1,\
        patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.is_pr_ok",return_value=False) as mock_is_pr_ok1,\
        patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.is_power_total_ok",return_value=True) as mock_is_power_ok1:
        await sensor1._handle_update(data)

        mock_is_power_ok1.assert_called_once()
        mock_is_pr_ok1.assert_called_once()
        mock_write_ha_state1.assert_not_called()

        args, kwargs = mock_is_pr_ok1.call_args

        assert args[0] == pr
        assert sensor1._attr_native_value is None

@pytest.mark.asyncio
async def test_pv_self_consumption__handle_update_power_nicht_ok(caplog):
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

    with patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.PvSelfConsumption.async_write_ha_state", 
               new_callable=MagicMock
               ) as mock_write_ha_state1,\
        patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.is_pr_ok",return_value=True) as mock_is_pr_ok1,\
        patch("custom_components.maxxi_charge_connect.devices.pv_self_consumption.is_power_total_ok",return_value=False) as mock_is_power_ok1:
        await sensor1._handle_update(data)

        mock_is_power_ok1.assert_called_once()
        mock_is_pr_ok1.assert_not_called()
        mock_write_ha_state1.assert_not_called()

        args, kwargs = mock_is_power_ok1.call_args

        assert args[0] == float(data.get("PV_power_total", 0))
        assert args[1] == data.get("batteriesInfo", [])
        assert sensor1._attr_native_value is None
