from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
from homeassistant.components.sensor import (
    SensorDeviceClass,    
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_soe import (
    BatterySoE,
)

@pytest.mark.asyncio
async def test_battery_soe__init(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    
    sensor = BatterySoE(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_device_class == None    
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.WATT_HOUR
    assert sensor.icon == "mdi:home-battery"
    assert sensor._attr_unique_id == "1234abcd_battery_soe"
    assert sensor._attr_native_value is None
    

@pytest.mark.asyncio
@patch("custom_components.maxxi_charge_connect.devices.battery_soe.async_dispatcher_connect")
async def test_battery_soe__async_added_to_hass(mock_dispatcher_connect):
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

    sensor = BatterySoE(dummy_config_entry)
    sensor.hass = hass
        
    await sensor.async_added_to_hass()

    mock_dispatcher_connect.assert_called_once()
    args, kwargs = mock_dispatcher_connect.call_args

    assert args[0] is hass
    assert args[1] == f"{DOMAIN}_{dummy_config_entry.data[CONF_WEBHOOK_ID]}_update_sensor"
    assert args[2].__name__ == "_handle_update"


@pytest.mark.asyncio
async def test_battery_soe__device_info(caplog):

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoE(dummy_config_entry)
    
    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soe__handle_update_alles_ok(caplog):
    
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}
    
    capacity = 1187.339966

    data = {        
        "batteriesInfo": [
            {
                "batteryCapacity": capacity
            }
        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_soe.BatterySoE.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == capacity

@pytest.mark.asyncio
async def test_battery_soe__handle_update_keine_batterien(caplog):
    
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}
    

    data = {        
        "batteriesInfo": [

        ]
    }

    sensor = BatterySoE(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_soe.BatterySoE.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_not_called()

    assert sensor._attr_native_value is None
