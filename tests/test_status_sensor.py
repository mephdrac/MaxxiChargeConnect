"""Tests für den StatusSensor der MaxxiChargeConnect-Integration."""

from unittest.mock import MagicMock

import pytest

from custom_components.maxxi_charge_connect.const import (
    CCU,
    CONF_DEVICE_ID,
    DOMAIN,
    ERROR,
    ERRORS,
    PROXY_ERROR_DEVICE_ID,
)
from custom_components.maxxi_charge_connect.devices.status_sensor import StatusSensor


@pytest.fixture
def sensor():
    """Erstellt einen StatusSensor mit Dummy-ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {CONF_DEVICE_ID: "device-123"}

    sensor_obj = StatusSensor(entry)
    sensor_obj.hass = MagicMock()
    return sensor_obj


def test_status_sensor_device_info(sensor):
    """device_info sollte vom BaseWebhookSensor kommen."""
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"


@pytest.mark.asyncio
async def test_status_sensor_handle_update_ok(sensor):
    """OK-Event setzt integration_state als native_value."""
    payload = {
        PROXY_ERROR_DEVICE_ID: "device-123",
        "integration_state": "OK",
    }

    await sensor.handle_update(payload)

    assert sensor.native_value == "OK"
    assert sensor.extra_state_attributes == payload


@pytest.mark.asyncio
async def test_status_sensor_handle_update_error(sensor):
    """Error-Event setzt Fehlertext als native_value."""
    payload = {
        CCU: "device-123",
        PROXY_ERROR_DEVICE_ID: ERRORS,
        ERROR: "boom",
    }

    await sensor.handle_update(payload)

    assert sensor.native_value == "Fehler (boom)"
    assert sensor.extra_state_attributes == payload


@pytest.mark.asyncio
async def test_status_sensor_handle_stale_keeps_available(sensor):
    """Stale soll StatusSensor verfügbar lassen und letzten Wert behalten."""
    sensor._attr_available = True  # pylint: disable=protected-access
    sensor._attr_native_value = "OK"  # pylint: disable=protected-access

    await sensor.handle_stale()

    assert sensor.available is True
    assert sensor.native_value == "OK"
