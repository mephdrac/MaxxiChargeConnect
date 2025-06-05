import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID

from .const import DOMAIN


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            webhook_id = user_input[CONF_WEBHOOK_ID]
            return self.async_create_entry(
                title=f"MaxxiCharge-{webhook_id}", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_WEBHOOK_ID): str}),
        )
