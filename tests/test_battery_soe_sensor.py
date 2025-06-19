from unittest.mock import MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfEnergy
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.battery_soe_sensor import (
    BatterySoESensor,
)

@pytest.mark.asyncio
async def test_battery_soe_sensor__init(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    # batteries = [{} "batteryCapacity": 1187.339966 }]
    sensor = BatterySoESensor(dummy_config_entry, 0)

    # Grundlegende Attribute prüfen
    assert sensor._attr_entity_registry_enabled_default == True
    assert sensor._attr_translation_key == "BatterySoESensor"
    assert sensor._attr_has_entity_name == True
    assert sensor._index == 0
    assert sensor._attr_translation_placeholders == {"index": str(0 + 1)}
    assert sensor._entry == dummy_config_entry
    assert sensor._attr_suggested_display_precision == 2
    assert sensor._attr_native_unit_of_measurement == UnitOfEnergy.WATT_HOUR
    assert sensor.icon == "mdi:home-battery"
    assert sensor._attr_unique_id == "1234abcd_battery_soe_0"
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_battery_soe_sensor__async_added_to_hass(caplog):
    hass = MagicMock()
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "abc123"

    listeners_mock = MagicMock()
    hass.data = {
        "maxxi_charge_connect": {
            "abc123": {
                "listeners": listeners_mock
            }
        }
    }

    dummy_config_entry.data = {
        CONF_WEBHOOK_ID: "Webhook_ID"
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)
    sensor.hass = hass
        
    await sensor.async_added_to_hass()

    # Jetzt kannst du prüfen, ob .append aufgerufen wurde:
    listeners_mock.append.assert_called_once_with(sensor._handle_update)

@pytest.mark.asyncio
async def test_battery_soe_sensor__device_info(caplog):

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoESensor(dummy_config_entry, 0)
        
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update_alles_ok(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}
        
    bat = 1187.339966
    data = {    
        "batteriesInfo": [
            {
                "batteryCapacity": bat
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 0)

    with patch("custom_components.maxxi_charge_connect.devices.battery_soe_sensor.BatterySoESensor.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == bat


@pytest.mark.asyncio
async def test_battery_soe_sensor__handle_update__index_error(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}
        
    bat = 1187.339966
    data = {    
        "batteriesInfo": [
            {
                "batteryCapacity": bat
            }
        ]
    }

    sensor = BatterySoESensor(dummy_config_entry, 10)

    with patch("custom_components.maxxi_charge_connect.devices.battery_soe_sensor.BatterySoESensor.async_write_ha_state", new_callable=MagicMock
               ) as mock_write_ha_state:
        await sensor._handle_update(data)
        mock_write_ha_state.assert_not_called()

    assert sensor._attr_native_value is None
