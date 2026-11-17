"""Exercise the V1 forms with schema validation as performed by Home Assistant."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID

from custom_components.maxxi_charge_connect.config_flow import MaxxiChargeConnectConfigFlow
from custom_components.maxxi_charge_connect.const import (
    CCU_V1,
    CONF_CCU_VERSION,
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_ENABLE_MQTT_BROKER,
    CONF_TIMEOUT_RECEIVE,
    DEFAULT_TIMEOUT_RECEIVE,
)


@pytest.fixture
def flow():
    """Use real forms and entry results, replacing only Home Assistant storage."""
    instance = MaxxiChargeConnectConfigFlow()
    instance.hass = MagicMock()
    instance._async_current_entries = MagicMock(return_value=[])
    instance.async_set_unique_id = AsyncMock()
    instance._abort_if_unique_id_configured = MagicMock()
    return instance


@pytest.mark.asyncio
@pytest.mark.parametrize("proxy", [False, True])
async def test_v1_setup_with_default_network_settings(flow, proxy):
    """Require a CCU IP for the local proxy while keeping it optional for webhooks."""
    result = await flow.async_step_user({CONF_CCU_VERSION: CCU_V1})
    assert result["step_id"] == "v1"

    v1_input = {
        CONF_NAME: "CCU V1",
        CONF_DEVICE_ID: "123",
        CONF_WEBHOOK_ID: "hook",
    }
    user_input = result["data_schema"](v1_input)
    assert user_input == v1_input

    result = await flow.async_step_v1(user_input)
    assert result["step_id"] == "optional"

    ccu_ip = "192.168.1.100" if proxy else ""
    user_input = result["data_schema"](
        {
            CONF_ENABLE_LOCAL_CLOUD_PROXY: proxy,
            CONF_IP_ADDRESS: ccu_ip,
        }
    )

    result = await flow.async_step_optional(user_input)

    if proxy:
        assert result["step_id"] == "proxy_options"
        result = await flow.async_step_proxy_options(result["data_schema"]({}))

    assert result["type"] == "create_entry"
    assert result["data"][CONF_CCU_VERSION] == CCU_V1
    assert result["data"][CONF_WEBHOOK_ID] == "hook"
    assert result["data"][CONF_TIMEOUT_RECEIVE] == DEFAULT_TIMEOUT_RECEIVE
    assert result["data"][CONF_IP_ADDRESS] == (ccu_ip or None)
    assert result["data"][CONF_ENABLE_LOCAL_CLOUD_PROXY] is proxy
    assert not result["data"][CONF_ENABLE_MQTT_BROKER]


@pytest.mark.asyncio
async def test_v1_proxy_requires_ccu_ip(flow):
    """Reject proxy activation without a CCU IP address."""
    await flow.async_step_user({CONF_CCU_VERSION: CCU_V1})
    await flow.async_step_v1(
        {
            CONF_NAME: "CCU V1",
            CONF_DEVICE_ID: "123",
            CONF_WEBHOOK_ID: "hook",
        }
    )

    result = await flow.async_step_optional(
        {
            CONF_ENABLE_LOCAL_CLOUD_PROXY: True,
            CONF_IP_ADDRESS: "",
        }
    )

    assert result["type"] == "form"
    assert result["step_id"] == "optional"
    assert result["errors"] == {CONF_IP_ADDRESS: "required"}


@pytest.mark.asyncio
async def test_empty_optional_and_proxy_submissions_advance(flow):
    """Empty submissions are valid for steps with optional fields."""
    await flow.async_step_user({CONF_CCU_VERSION: CCU_V1})
    await flow.async_step_v1({CONF_NAME: "CCU", CONF_DEVICE_ID: "123", CONF_WEBHOOK_ID: "hook"})
    assert (await flow.async_step_optional({}))["type"] == "create_entry"
    assert (await flow.async_step_proxy_options({}))["type"] == "create_entry"


@pytest.mark.asyncio
async def test_v1_duplicate_error_matches_form_field(flow):
    """Report duplicate IDs against the actual schema key."""
    flow._async_current_entries.return_value = [MagicMock(data={CONF_DEVICE_ID: "123"})]
    result = await flow.async_step_v1({CONF_NAME: "CCU", CONF_DEVICE_ID: "123", CONF_WEBHOOK_ID: "hook"})
    assert result["errors"] == {CONF_DEVICE_ID: "device_exists"}


@pytest.mark.asyncio
async def test_reconfigure_v1_without_ip(flow):
    """Legacy entries with a null IP still produce a valid optional form."""
    entry = MagicMock(data={CONF_NAME: "CCU", CONF_DEVICE_ID: "123", CONF_WEBHOOK_ID: "hook"})
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    result = await flow.async_step_reconfigure()
    assert result["step_id"] == "v1"
    result = await flow.async_step_v1(result["data_schema"]({}))
    user_input = result["data_schema"]({})
    assert user_input[CONF_IP_ADDRESS] == ""
    assert user_input[CONF_TIMEOUT_RECEIVE] == DEFAULT_TIMEOUT_RECEIVE
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    await flow.async_step_optional(user_input)
    updates = flow.async_update_reload_and_abort.call_args.kwargs["data_updates"]
    assert updates[CONF_CCU_VERSION] == CCU_V1
    assert not updates[CONF_ENABLE_CLOUD_DATA]
