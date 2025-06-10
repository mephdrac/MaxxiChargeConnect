import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID, CONF_HOST

from .const import DOMAIN


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            webhook_id = user_input[CONF_WEBHOOK_ID]
            hosts = user_input[CONF_HOST]
            return self.async_create_entry(
                title=f"MaxxiCharge-{webhook_id}",
                data={CONF_WEBHOOK_ID: webhook_id, CONF_HOST: hosts},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WEBHOOK_ID): str,
                    vol.Required(CONF_HOST): str,  # ← hier kommt die IP / Hostname rein
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return MaxxiChargeOptionsFlowHandler(config_entry)

    async def async_migrate_entry(hass, config_entry):
        """Migrate old entry to new version."""
        if config_entry.version == 1:
            new_data = {**config_entry.data}

            # Setze z. B. einen Default-Wert oder lasse den Nutzer migrieren
            # new_data[CONF_HOST] = "maxxi.local"  # <- Dummy oder Migration notwendig

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
                        CONF_HOST,
                        default=self.config_entry.options.get(
                            CONF_HOST, self.config_entry.data.get(CONF_HOST, "")
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
