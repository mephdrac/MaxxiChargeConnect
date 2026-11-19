"""Tests für den StatusSensor der MaxxiChargeConnect-Integration."""

from unittest.mock import MagicMock

import pytest

from custom_components.maxxi_charge_connect.const import (
    CCU,
    CONF_DEVICE_ID,
    DOMAIN,
    ERROR,
    ERRORS,
    HTTP_SCAN_EVENTNAME,
    PROXY_ERROR_DEVICE_ID,
    PROXY_STATUS_EVENTNAME,
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
async def test_status_sensor_startup_telemetry_and_timeout(sensor):
    """Remain offline until telemetry arrives and return offline on timeout."""
    sensor.async_write_ha_state = MagicMock()
    payload = {PROXY_ERROR_DEVICE_ID: "device-123", "integration_state": "OK"}

    assert sensor.available is True
    assert sensor.native_value == "Offline"
    await sensor.async_update_from_event(MagicMock(event_type=HTTP_SCAN_EVENTNAME, data={"payload": payload}))
    assert sensor.native_value == "Offline"

    await sensor.async_update_from_event(MagicMock(event_type=PROXY_STATUS_EVENTNAME, data={"payload": payload}))
    assert sensor.native_value == "OK"
    sensor.async_write_ha_state.assert_called_once()

    await sensor._wrapper_stale(None)
    assert sensor.available is True
    assert sensor.native_value == "Offline"
    assert sensor.extra_state_attributes == {}


@pytest.mark.asyncio
async def test_http_scan_diagnosis_survives_webhook(sensor):
    """A healthy Webhook must not hide a failed HTTP scan."""
    sensor._http_scan_coordinator = MagicMock(
        scan_target="192.168.60.27:5000",
        scan_result="Zeitüberschreitung",
    )
    sensor.async_write_ha_state = MagicMock()
    payload = {PROXY_ERROR_DEVICE_ID: "device-123", "integration_state": "OK"}
    await sensor.async_update_from_event(MagicMock(event_type=PROXY_STATUS_EVENTNAME, data={"payload": payload}))

    assert sensor.native_value == "OK"
    assert sensor.extra_state_attributes["http_scan_target"] == "192.168.60.27:5000"
    assert sensor.extra_state_attributes["http_scan_result"] == "Zeitüberschreitung"
