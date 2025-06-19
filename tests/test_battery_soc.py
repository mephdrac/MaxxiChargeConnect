from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower, PERCENTAGE
from homeassistant.components.sensor import (
    SensorDeviceClass,    
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_soc import (
    BatterySoc,
)

@pytest.mark.asyncio
async def test_battery_soc__init(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    
    sensor = BatterySoc(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry    
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    assert sensor._attr_native_unit_of_measurement == PERCENTAGE
    assert sensor.icon == "mdi:battery-unknown"
    assert sensor._attr_unique_id == "1234abcd_battery_soc"
    assert sensor._attr_native_value is None

@pytest.mark.asyncio
@patch("custom_components.maxxi_charge_connect.devices.battery_soc.async_dispatcher_connect")
async def test_battery_soc__async_added_to_hass(mock_dispatcher_connect):
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

    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass
        
    await sensor.async_added_to_hass()

    mock_dispatcher_connect.assert_called_once()
    args, kwargs = mock_dispatcher_connect.call_args

    assert args[0] is hass
    assert args[1] == f"{DOMAIN}_{dummy_config_entry.data[CONF_WEBHOOK_ID]}_update_sensor"
    assert args[2].__name__ == "_handle_update"


@pytest.mark.asyncio
async def test_battery_soc__device_info(caplog):

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoc(dummy_config_entry)
    
    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soc__handle_update_alles_ok(caplog):
    # is_pccu_ok(ccu) == true 
    # is_power_total_ok(pv_power, batteries) == true
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}
    
    soc = 37.623    

    data = {
        "SOC": soc        
    }

    sensor = BatterySoc(dummy_config_entry)

    with patch("custom_components.maxxi_charge_connect.devices.battery_soc.BatterySoc.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == soc


@pytest.mark.asyncio
async def test_battery_soc__icon_0_Prozent(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 0

    assert sensor.icon == "mdi:battery-outline"

@pytest.mark.asyncio
async def test_battery_soc__icon_18_Prozent(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 18

    assert sensor.icon == "mdi:battery-20"

@pytest.mark.asyncio
async def test_battery_soc__icon_38_Prozent(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 38

    assert sensor.icon == "mdi:battery-40"

@pytest.mark.asyncio
async def test_battery_soc__icon_38_Prozent(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 38

    assert sensor.icon == "mdi:battery-40"


@pytest.mark.asyncio
async def test_battery_soc__icon_100_Prozent(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 100

    assert sensor.icon == "mdi:battery"