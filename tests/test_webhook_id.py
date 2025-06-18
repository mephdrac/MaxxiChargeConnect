from unittest.mock import MagicMock
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory

import pytest
from custom_components.maxxi_charge_connect.devices.webhook_id import (
    WebhookId,
)

@pytest.mark.asyncio
async def test_webhook_id__init(caplog):
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    dummy_config_entry.data = {
        CONF_WEBHOOK_ID: "Webhook_ID"
    }
    sensor = WebhookId(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._attr_native_value == dummy_config_entry.data[CONF_WEBHOOK_ID]
    assert sensor._attr_translation_key == "WebhookId"
    assert sensor._entry == dummy_config_entry    
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.icon == "mdi:webhook"
    assert sensor._attr_unique_id == "1234abcd_webhook_id"


@pytest.mark.asyncio
async def test_webhook_id__set_value(caplog):
            
    dummy_config_entry = MagicMock()
    test_text = "MeinTest"

    sensor = WebhookId(dummy_config_entry)
    sensor.set_value(test_text)

    # Grundlegende Attribute prüfen
    assert sensor._attr_native_value == test_text
    
    
@pytest.mark.asyncio
async def test_webhook_id__device_info(caplog):

    dummy_config_entry = MagicMock()    
    dummy_config_entry.title = "Test Entry"

    sensor = WebhookId(dummy_config_entry)
        
    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title
