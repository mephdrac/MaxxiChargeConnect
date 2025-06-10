import voluptuous as vol
import uuid


from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID, CONF_IP_ADDRESS, CONF_NAME

from .const import DOMAIN

from homeassistant.helpers.selector import BooleanSelector


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    _name = None
    _webhook_id = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._webhook_id = user_input[CONF_WEBHOOK_ID]
            restrict = user_input["restrict_host"]

            if restrict:
                return await self.async_step_host()

            return self.async_create_entry(
                title=self._name,
                data={CONF_WEBHOOK_ID: self._webhook_id, CONF_NAME: self._name},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): Strin,
                    vol.Required(CONF_WEBHOOK_ID): str,
                    vol.Optional("restrict_host", default=False): BooleanSelector(),
                }
            ),
        )

    async def async_step_host(self, user_input=None):
        if user_input is not None:
            hosts = user_input[CONF_IP_ADDRESS]
            return self.async_create_entry(
                title=self._name,
                data={CONF_WEBHOOK_ID: self._webhook_id, CONF_IP_ADDRESS: hosts},
            )

        return self.async_show_form(
            step_id="host",
            data_schema=vol.Schema({vol.Required(CONF_IP_ADDRESS): str}),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return MaxxiChargeOptionsFlowHandler(config_entry)

    async def async_migrate_entry(hass, config_entry):
        """Migrate old entry to new version."""
        if config_entry.version == 1:
            new_data = {**config_entry.data}

            # Setze z. B. einen Default-Wert oder lasse den Nutzer migrieren
            # new_data[CONF_NAME] = config_entry.data.get(CONF_NAME, config_entry.title)

            config_entry.version = 2
            hass.config_entries.async_update_entry(config_entry, data=new_data)
            return True

        return False


class MaxxiChargeOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=self.config_entry.options.get(
                            CONF_NAME,
                            self.config_entry.data.get(
                                CONF_NAME, self.config_entry.title
                            ),
                        ),
                    ): str,
                    vol.Required(
                        CONF_WEBHOOK_ID,
                        default=self.config_entry.options.get(
                            CONF_WEBHOOK_ID,
                            self.config_entry.data.get(CONF_WEBHOOK_ID, ""),
                        ),
                    ): str,
                }
            ),
        )
