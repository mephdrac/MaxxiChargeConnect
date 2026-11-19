"""Regression tests for webhook ownership and device isolation."""

from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.webhook import async_register
from homeassistant.const import CONF_WEBHOOK_ID

from custom_components.maxxi_charge_connect.const import CONF_DEVICE_ID, DOMAIN, WEBHOOK_SIGNAL_UPDATE
from custom_components.maxxi_charge_connect.webhook import async_register_webhook, async_unregister_webhook


@pytest.fixture
def setup_webhook(monkeypatch):
    """Capture the webhook callback without running an HTTP server or watchdog."""
    hass = MagicMock()
    entry = MagicMock(entry_id="entry-1", data={CONF_WEBHOOK_ID: "webhook-secret", CONF_DEVICE_ID: "ccu-1"})
    hass.data = defaultdict(dict, {DOMAIN: {entry.entry_id: {}}})
    module = "custom_components.maxxi_charge_connect.webhook"
    register = MagicMock(side_effect=async_register)
    monkeypatch.setattr(f"{module}.async_register", register)
    monkeypatch.setattr(f"{module}.ir.async_delete_issue", MagicMock())
    monkeypatch.setattr(f"{module}.ir.async_create_issue", MagicMock())
    dispatch = MagicMock()
    monkeypatch.setattr(f"{module}.async_dispatcher_send", dispatch)
    return hass, entry, register, dispatch


@pytest.mark.asyncio
async def test_mismatching_webhook_payload_never_reaches_sensors(setup_webhook):
    """Verify validation happens before updating dispatcher listeners."""
    hass, entry, register, dispatch = setup_webhook
    await async_register_webhook(hass, entry)
    handler = register.call_args.args[-1]
    request = MagicMock(json=AsyncMock(return_value={"deviceId": "ccu-2", "sendCount": 1}))

    response = await handler(hass, "webhook-secret", request)

    assert response.status == 403
    dispatch.assert_not_called()
    assert "webhook-secret" not in hass.data[DOMAIN][entry.entry_id][WEBHOOK_SIGNAL_UPDATE]


@pytest.mark.asyncio
async def test_webhook_rotation_releases_original_id(setup_webhook):
    """Unload unregisters the old ID after the configuration is updated."""
    hass, entry, _, _ = setup_webhook
    await async_register_webhook(hass, entry)
    other_handler = AsyncMock()
    async_register(hass, "other", "Other integration", "other-id", other_handler)

    entry.data = {**entry.data, CONF_WEBHOOK_ID: "other-id"}
    await async_unregister_webhook(hass, entry)
    with pytest.raises(ValueError, match="already defined"):
        await async_register_webhook(hass, entry)
    async_register(hass, "other", "Other integration", "webhook-secret", other_handler)
