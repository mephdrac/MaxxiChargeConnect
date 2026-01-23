""""Tests für die HttpScanText Entity."""

from unittest.mock import MagicMock
from homeassistant.const import EntityCategory
import pytest
from custom_components.maxxi_charge_connect.http_scan.http_scan_text import (
    HttpScanText,
)


@pytest.mark.asyncio
async def test_http_scan_text__init():
    """Testet die Initialisierung der HttpScanText Entity."""

    testname = "TestName"
    keyname = "TestKeyname"
    coordinator = MagicMock()
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor._attr_translation_key == keyname  # pylint: disable=protected-access
    assert sensor.coordinator == coordinator
    assert sensor._keyname == keyname  # pylint: disable=protected-access
    assert sensor._entry == coordinator.entry  # pylint: disable=protected-access
    assert sensor._attr_unique_id == f"{coordinator.entry.entry_id}_{keyname}"  # pylint: disable=protected-access

    assert sensor._attr_icon == icon  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC  # pylint: disable=protected-access
    assert sensor._attr_should_poll is False  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_http_scan_text__native_value():
    """Testet die native_value Eigenschaft der HttpScanText Entity."""

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "TestKeyname"
    coordinator = MagicMock()
    coordinator.data = {keyname: testvalue}
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor.native_value == testvalue


@pytest.mark.asyncio
async def test_http_scan_text__native_value2():
    """Testet die native_value Eigenschaft der HttpScanText Entity mit fehlendem Key."""

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "Keyname"
    coordinator = MagicMock()
    coordinator.data = {"key": testvalue}
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)

    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_http_scan_text__set_value():
    """Testet die set_value Methode der HttpScanText Entity."""

    testvalue = "MeinTest"
    testname = "TestName"
    keyname = "Keyname"
    coordinator = MagicMock()
    icon = "mdi:flash"

    sensor = HttpScanText(coordinator=coordinator, keyname=keyname, name=testname, icon=icon)
    sensor.set_value(testvalue)

    assert sensor._attr_native_value == testvalue  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_http_scan_text__device_info():
    """Testet die device_info Eigenschaft der HttpScanText Entity."""

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
