"""Tests for removing the obsolete webhook ID entity."""

from unittest.mock import MagicMock, patch

from custom_components.maxxi_charge_connect import _remove_legacy_webhook_entity
from custom_components.maxxi_charge_connect.const import DOMAIN


def test_remove_legacy_webhook_entity():
    """Remove only the webhook ID entity belonging to the current config entry."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "ccu_1"

    registry = MagicMock()
    registry.entities = {
        "text.ccu_1_webhook": MagicMock(
            config_entry_id="ccu_1",
            platform=DOMAIN,
            unique_id="ccu_1_webhook_id",
        ),
        "text.ccu_2_webhook": MagicMock(
            config_entry_id="ccu_2",
            platform=DOMAIN,
            unique_id="ccu_2_webhook_id",
        ),
        "text.other_integration": MagicMock(
            config_entry_id="other_entry",
            platform="other_integration",
            unique_id="ccu_1_webhook_id",
        ),
        "sensor.ccu_1_battery": MagicMock(
            config_entry_id="ccu_1",
            platform=DOMAIN,
            unique_id="ccu_1_battery_soc",
        ),
    }

    entry.data = {"webhook_id": "secret-webhook-id"}

    with patch(
        "custom_components.maxxi_charge_connect.er.async_get",
        return_value=registry,
    ):
        _remove_legacy_webhook_entity(hass, entry)

    registry.async_remove.assert_called_once_with("text.ccu_1_webhook")
    assert entry.data["webhook_id"] == "secret-webhook-id"
