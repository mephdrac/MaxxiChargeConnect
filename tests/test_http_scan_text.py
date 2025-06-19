from unittest.mock import MagicMock
from homeassistant.const import EntityCategory
import pytest
from custom_components.maxxi_charge_connect.http_scan.http_scan_text import (
    HttpScanText,
)

@pytest.mark.asyncio
async def test_http_scan_text__init(caplog):

    testname = "TestName"
    keyname = "TestKeyname"
    coordinator = MagicMock()
    icon = "mdi:flash"
    
    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor._attr_translation_key == keyname
    assert sensor.coordinator == coordinator
    assert sensor._keyname == keyname
    assert sensor._entry == coordinator.entry
    assert sensor._attr_unique_id == f"{coordinator.entry.entry_id}_{keyname}"

    assert sensor._attr_icon == icon
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_should_poll == False

@pytest.mark.asyncio
async def test_http_scan_text__native_value(caplog):

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "TestKeyname"
    coordinator = MagicMock()
    coordinator.data = {keyname: testvalue}
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor.native_value == testvalue

@pytest.mark.asyncio
async def test_http_scan_text__native_value2(caplog):

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "Keyname"
    coordinator = MagicMock()
    coordinator.data = {"key": testvalue}
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor.native_value is None

@pytest.mark.asyncio
async def test_http_scan_text__set_value(caplog):

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "Keyname"
    coordinator = MagicMock()    
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)
    sensor.set_value(testvalue)

    assert sensor._attr_native_value == testvalue

@pytest.mark.asyncio
async def test_http_scan_text__device_info(caplog):

    title = "TestTitle"
    testname = "TestName"
    keyname = "Keyname"
    coordinator = MagicMock()
    coordinator.entry.title = title
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == title
