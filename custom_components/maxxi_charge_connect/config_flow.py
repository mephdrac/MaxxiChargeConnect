import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import BooleanSelector

from .migration.migration_from_yaml import MigrateFromYaml
from .webhook import async_unregister_webhook

from .const import DOMAIN, ONLY_ONE_IP, NOTIFY_MIGRATION, \
    CONF_ENABLE_LOCAL_CLOUD_PROXY, \
    CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD, \
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die MaxxiChargeConnect Integration.

    Unterstützt den Standard-Setup-Flow sowie einen Reconfigure-Flow,
    um bestehende Einträge zu ändern.
    """

    VERSION = 3
    MINOR_VERSION = 2
    reconfigure_supported = True

    _name = None
    _webhook_id: str = ""
    _host_ip = None
    _only_ip = False
    _notify_migration = False
    _enable_local_cloud_proxy = False    
    _enable_forward_to_cloud = DEFAULT_ENABLE_FORWARD_TO_CLOUD
    _device_id = None

    @property
    def webhook_id(self) -> str:
        """Öffentlicher Zugriff auf _webhook_id."""
        return self._webhook_id

    async def async_step_user(self, user_input=None):
        """Erster Schritt des Setup-Flows, der die Nutzereingaben abfragt."""

        if user_input is not None:
            if not user_input.get(CONF_DEVICE_ID):
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_NAME): str,
                            vol.Required(CONF_DEVICE_ID): str,
                            vol.Required(CONF_WEBHOOK_ID): str,
                            vol.Optional(CONF_IP_ADDRESS, default=""): str,
                            vol.Optional(ONLY_ONE_IP, default=False): BooleanSelector(),
                            vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                            vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=DEFAULT_ENABLE_LOCAL_CLOUD_PROXY): BooleanSelector(),
                            vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=DEFAULT_ENABLE_FORWARD_TO_CLOUD): BooleanSelector()
                        }
                    ),
                    errors={"device_id": "required"},
                )

            self._name = user_input[CONF_NAME]
            self._device_id = user_input[CONF_DEVICE_ID]
            self._webhook_id = user_input[CONF_WEBHOOK_ID]
            self._host_ip = user_input.get(CONF_IP_ADDRESS, None)
            self._only_ip = user_input.get(ONLY_ONE_IP, False)
            self._notify_migration = user_input.get(NOTIFY_MIGRATION, False)
            self._enable_local_cloud_proxy = user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)            
            self._enable_forward_to_cloud = user_input.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)

            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_NAME: self._name,
                    CONF_DEVICE_ID: self._device_id,
                    CONF_IP_ADDRESS: self._host_ip,
                    ONLY_ONE_IP: self._only_ip,
                    NOTIFY_MIGRATION: self._notify_migration,
                    CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,                    
                    CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_WEBHOOK_ID): str,
                    vol.Optional(CONF_IP_ADDRESS, default=""): str,
                    vol.Optional(ONLY_ONE_IP, default=False): BooleanSelector(),
                    vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=DEFAULT_ENABLE_LOCAL_CLOUD_PROXY): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=DEFAULT_ENABLE_FORWARD_TO_CLOUD): BooleanSelector()
                }
            ),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Flow-Schritt für die Neukonfiguration eines bestehenden Eintrags."""

        entry = self._get_reconfigure_entry()

        if user_input is not None:
            if not user_input.get(CONF_DEVICE_ID):
                current_data = entry.data
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_WEBHOOK_ID, default=current_data.get(CONF_WEBHOOK_ID, "")): str,
                            vol.Required(CONF_DEVICE_ID, default=current_data.get(CONF_DEVICE_ID, "")): str,
                            vol.Optional(CONF_IP_ADDRESS, default=current_data.get(CONF_IP_ADDRESS, "")): str,
                            vol.Optional(ONLY_ONE_IP, default=current_data.get(ONLY_ONE_IP, False)): BooleanSelector(),
                            vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                            vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=current_data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY)): BooleanSelector(),
                            vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=current_data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)): BooleanSelector()
                        }
                    ),
                    errors={"device_id": "required"},
                )

            if user_input.get(NOTIFY_MIGRATION):
                migrator = MigrateFromYaml(self.hass, entry)
                await migrator.async_notify_possible_migration()

            old_webhook_id = entry.data.get(CONF_WEBHOOK_ID)
            new_data = {                
                CONF_WEBHOOK_ID: user_input[CONF_WEBHOOK_ID],
                CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],                
                CONF_IP_ADDRESS: user_input.get(CONF_IP_ADDRESS, ""),
                ONLY_ONE_IP: user_input.get(ONLY_ONE_IP, False),
                CONF_ENABLE_LOCAL_CLOUD_PROXY: user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY),                
                CONF_ENABLE_FORWARD_TO_CLOUD: user_input.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)
            }

            self._abort_if_unique_id_mismatch()

            await async_unregister_webhook(
                self.hass, entry, old_webhook_id=old_webhook_id
            )

            return self.async_update_reload_and_abort(
                entry,
                data_updates=new_data,
            )

        current_data = entry.data

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WEBHOOK_ID, default=current_data.get(CONF_WEBHOOK_ID, "")): str,
                    vol.Required(CONF_DEVICE_ID, default=current_data.get(CONF_DEVICE_ID, "")): str,
                    vol.Optional(CONF_IP_ADDRESS, default=current_data.get(CONF_IP_ADDRESS, "")): str,
                    vol.Optional(ONLY_ONE_IP, default=current_data.get(ONLY_ONE_IP, False)): BooleanSelector(),
                    vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=current_data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY)): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=current_data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)): BooleanSelector()
                }
            ),
        )

    async def async_step_fix_device_id(self, user_input=None):
        """Schritt zum Nachtragen der device_id, falls sie fehlt (z.B. nach Migration)."""

        entry = self._get_reconfigure_entry()
        current_data = dict(entry.data)

        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID)
            if not device_id:
                return self.async_show_form(
                    step_id="fix_device_id",
                    data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): str}),
                    errors={"device_id": "required"},
                )
            # Update existing entry with device_id
            current_data[CONF_DEVICE_ID] = device_id
            self.hass.config_entries.async_update_entry(entry, data=current_data)
            # Flow beenden, kein neuer Eintrag wird erstellt
            return self.async_abort(reason="device_id_updated")

        return self.async_show_form(
            step_id="fix_device_id",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): str}),
        )

    def is_matching(self, other: config_entries.ConfigFlow) -> bool:
        """Vergleicht, ob dieser Flow einem bestehenden Flow entspricht."""
        if not isinstance(other, MaxxiChargeConnectConfigFlow):
            return False
        return self.webhook_id == other.webhook_id
