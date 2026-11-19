"""Verify access control for the local MaxxiChargeConnect cloud proxy.

The proxy must accept HTTP requests only when the device identifier and the
TCP peer address match an enabled CCU configuration entry. All requests are
mocked; these tests neither start a listener nor contact the Maxxisun cloud.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_IP_ADDRESS

from custom_components.maxxi_charge_connect.const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    PROXY_ERROR_DEVICE_ID,
)
from custom_components.maxxi_charge_connect.reverse_proxy.proxy_server import MaxxiProxyServer


@pytest.fixture
def proxy():
    """Create a proxy with one configured CCU and mocked Home Assistant."""
    entry = SimpleNamespace(
        entry_id="entry-1",
        state=ConfigEntryState.LOADED,
        data={
            CONF_DEVICE_ID: "ccu-123",
            CONF_IP_ADDRESS: "192.0.2.10",
            CONF_ENABLE_LOCAL_CLOUD_PROXY: True,
            CONF_ENABLE_FORWARD_TO_CLOUD: False,
            CONF_ENABLE_CLOUD_DATA: False,
        },
    )
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    return MaxxiProxyServer(hass), entry


def make_request(address="192.0.2.10", *, device_id="ccu-123", payload=None):
    """Build an HTTP request exposing a controlled TCP peer address."""
    request = MagicMock()
    request.transport.get_extra_info.return_value = (address, 12345)
    request.query = {PROXY_ERROR_DEVICE_ID: device_id}
    request.json = AsyncMock(return_value=payload if payload is not None else {PROXY_ERROR_DEVICE_ID: device_id})
    return request


@pytest.mark.parametrize(
    ("address", "device_id", "enabled", "configured_ip", "authorized"),
    [
        ("192.0.2.10", "ccu-123", True, "192.0.2.10", True),
        ("192.0.2.11", "ccu-123", True, "192.0.2.10", False),
        ("192.0.2.10", "unknown", True, "192.0.2.10", False),
        ("192.0.2.10", "ccu-123", False, "192.0.2.10", False),
        ("192.0.2.10", "ccu-123", True, None, False),
        ("192.0.2.10", "ccu-123", True, "invalid-ip", False),
    ],
)
def test_authorization_checks_device_and_peer_ip(proxy, address, device_id, enabled, configured_ip, authorized):
    """Only the configured CCU at the configured IP is authorized."""
    server, entry = proxy
    entry.data[CONF_ENABLE_LOCAL_CLOUD_PROXY] = enabled
    entry.data[CONF_IP_ADDRESS] = configured_ip
    result = server._get_authorized_entry(make_request(address, device_id=device_id), device_id)
    assert (result is entry) is authorized


def test_authorization_uses_ip_and_device_id_from_same_loaded_entry(proxy):
    """A second CCU cannot use the first CCU's device ID."""
    server, entry = proxy
    other = SimpleNamespace(
        entry_id="entry-2",
        state=ConfigEntryState.LOADED,
        data={**entry.data, CONF_DEVICE_ID: "ccu-456", CONF_IP_ADDRESS: "192.0.2.11"},
    )
    server.hass.config_entries.async_entries.return_value = [entry, other]
    request = make_request("192.0.2.11")
    request.headers = {"X-Forwarded-For": "192.0.2.10"}
    assert server._get_authorized_entry(request, "ccu-123") is None
    assert server._get_authorized_entry(request, "ccu-456") is other

    other.state = ConfigEntryState.NOT_LOADED
    assert server._get_authorized_entry(request, "ccu-456") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["text", "config"])
async def test_unauthorized_http_requests_do_not_trigger_side_effects(proxy, endpoint):
    """Reject requests from another IP without forwarding or fetching data."""
    server, _ = proxy
    server._forward_to_cloud = AsyncMock()
    server._on_reverse_proxy_message = AsyncMock()
    server.fetch_cloud_config = AsyncMock()
    request = make_request("192.0.2.11")

    response = await (server._handle_text(request) if endpoint == "text" else server._handle_config(request))

    assert response.status == 403
    server._forward_to_cloud.assert_not_awaited()
    server._on_reverse_proxy_message.assert_not_awaited()
    server.fetch_cloud_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_text_request_is_processed_without_cloud_forwarding(proxy):
    """Process authorized CCU data while honoring disabled cloud forwarding."""
    server, _ = proxy
    server._forward_to_cloud = AsyncMock(return_value=False)
    server._on_reverse_proxy_message = AsyncMock()
    payload = {PROXY_ERROR_DEVICE_ID: "ccu-123", "sendCount": 1}

    response = await server._handle_text(make_request(payload=payload))

    assert response.status == 200
    server._forward_to_cloud.assert_awaited_once_with("ccu-123", False, payload, False)
    server._on_reverse_proxy_message.assert_awaited_once_with(payload, False)


@pytest.mark.asyncio
async def test_proxy_telemetry_refreshes_ccu_timeout(proxy, monkeypatch):
    """CCUs supplying sensor data through the proxy must time out too."""
    server, entry = proxy
    entry.data[CONF_ENABLE_CLOUD_DATA] = True
    record = MagicMock()
    monkeypatch.setattr("custom_components.maxxi_charge_connect.reverse_proxy.proxy_server.record_v1_telemetry", record)
    server._on_reverse_proxy_message = AsyncMock()

    response = await server._handle_text(make_request())

    assert response.status == 200
    record.assert_called_once_with(server.hass, entry)


@pytest.mark.asyncio
async def test_authorized_config_request_returns_cached_config(proxy):
    """Return the device's cached configuration without contacting the cloud."""
    server, _ = proxy
    server._device_config_cache["ccu-123"] = {"mode": "local"}
    server.fetch_cloud_config = AsyncMock()

    response = await server._handle_config(make_request())

    assert response.status == 200
    assert response.content_type == "application/json"
    assert "local" in response.text
    assert "Access-Control-Allow-Origin" not in response.headers
    server.fetch_cloud_config.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [[], "text", {}, {PROXY_ERROR_DEVICE_ID: None}])
async def test_invalid_text_payload_returns_bad_request(proxy, payload):
    """Reject malformed payloads before accessing device or network state."""
    server, _ = proxy
    server._forward_to_cloud = AsyncMock()

    response = await server._handle_text(make_request(payload=payload))

    assert response.status == 400
    server._forward_to_cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_config_without_device_id_returns_bad_request(proxy):
    """Reject configuration requests without a device identifier."""
    server, _ = proxy
    response = await server._handle_config(make_request(device_id=""))
    assert response.status == 400
