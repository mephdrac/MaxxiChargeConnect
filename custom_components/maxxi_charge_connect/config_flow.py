"""Konfigurationsfluss für MaxxiChargeConnect mit Duplicate-Prüfung"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import BooleanSelector

from .const import (
    DOMAIN,
    ONLY_ONE_IP,
    NOTIFY_MIGRATION,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    CONF_REFRESH_CONFIG_FROM_CLOUD,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow für MaxxiChargeConnect mit Duplicate-Prüfung."""

    VERSION = 3
    MINOR_VERSION = 3
    
    reconfigure_supported = True

    _name: str | None = None
    _webhook_id: str | None = None
    _device_id: str | None = None
    _host_ip: str | None = None
    _only_ip: bool = False
    _notify_migration: bool = False
    _enable_local_cloud_proxy: bool = False
    _enable_forward_to_cloud: bool = DEFAULT_ENABLE_FORWARD_TO_CLOUD
    _enable_cloud_data: bool = False
    _refresh_cloud_data: bool = False

    _entry: config_entries.ConfigEntry | None = None  # nur beim Reconfigure

    # ----------------------------------------
    # Step 1: Pflichtfelder
    # ----------------------------------------
    async def async_step_user(self, user_input=None):
        errors = {}
        defaults = self._get_defaults_for_user_step()

        if user_input:
            self._device_id = user_input.get(CONF_DEVICE_ID)
            self._name = user_input.get(CONF_NAME)
            self._webhook_id = user_input.get(CONF_WEBHOOK_ID)

            # Pflichtfeldprüfung
            if not self._device_id:
                errors["device_id"] = "required"
            if not self._name:
                errors["name"] = "required"
            if not self._webhook_id:
                errors["webhook_id"] = "required"

            # Duplicate-Prüfung nur beim Neuanlegen
            if self._entry is None:
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_DEVICE_ID) == self._device_id:
                        errors["device_id"] = "device_exists"
                        break

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._schema_user(defaults),
                    errors=errors,
                )

            return await self.async_step_optional()

        return self.async_show_form(
            step_id="user", data_schema=self._schema_user(defaults)
        )

    # ----------------------------------------
    # Step 2: optionale Felder + Proxy aktivieren
    # ----------------------------------------
    async def async_step_optional(self, user_input=None):
        defaults = self._get_defaults_for_optional_step()

        if user_input:
            self._host_ip = user_input.get(CONF_IP_ADDRESS)
            self._only_ip = user_input.get(ONLY_ONE_IP, False)
            self._notify_migration = user_input.get(NOTIFY_MIGRATION, False)
            self._enable_local_cloud_proxy = user_input.get(
                CONF_ENABLE_LOCAL_CLOUD_PROXY, False
            )

            if self._enable_local_cloud_proxy:
                return await self.async_step_proxy_options()

            return self._create_entry(entry=self._entry)

        return self.async_show_form(
            step_id="optional", data_schema=self._schema_optional(defaults)
        )

    # ----------------------------------------
    # Step 3: Proxy-Optionen
    # ----------------------------------------
    async def async_step_proxy_options(self, user_input=None):
        defaults = self._get_defaults_for_proxy_step()

        if user_input:
            self._enable_forward_to_cloud = user_input.get(
                CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
            )
            self._enable_cloud_data = user_input.get(CONF_ENABLE_CLOUD_DATA, False)
            self._refresh_cloud_data = user_input.get(
                CONF_REFRESH_CONFIG_FROM_CLOUD, False
            )
            return self._create_entry(entry=self._entry)

        return self.async_show_form(
            step_id="proxy_options", data_schema=self._schema_proxy_options(defaults)
        )

    # ----------------------------------------
    # Entry erstellen / aktualisieren
    # ----------------------------------------
    def _create_entry(self, entry=None):
        data = {
            CONF_NAME: self._name,
            CONF_DEVICE_ID: self._device_id,
            CONF_WEBHOOK_ID: self._webhook_id,
            CONF_IP_ADDRESS: self._host_ip or None,
            ONLY_ONE_IP: self._only_ip,
            NOTIFY_MIGRATION: self._notify_migration,
            CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
            CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud,
            CONF_ENABLE_CLOUD_DATA: self._enable_cloud_data,
            CONF_REFRESH_CONFIG_FROM_CLOUD: self._refresh_cloud_data,
        }

        if entry is not None:
            self.hass.config_entries.async_update_entry(
                entry, data=data, title=self._name
            )
            return self.async_update_reload_and_abort(entry, data_updates=data)

        return self.async_create_entry(title=self._name, data=data)

    # ----------------------------------------
    # Schema & Defaults
    # ----------------------------------------
    def _schema_user(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
                vol.Required(
                    CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")
                ): str,
                vol.Required(
                    CONF_WEBHOOK_ID, default=defaults.get(CONF_WEBHOOK_ID, "")
                ): str,
            }
        )

    def _schema_optional(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Optional(
                    CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, "")
                ): str,
                vol.Optional(
                    ONLY_ONE_IP, default=defaults.get(ONLY_ONE_IP, False)
                ): BooleanSelector(),
                vol.Optional(
                    NOTIFY_MIGRATION, default=defaults.get(NOTIFY_MIGRATION, False)
                ): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLE_LOCAL_CLOUD_PROXY,
                    default=defaults.get(
                        CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY
                    ),
                ): BooleanSelector(),
            }
        )

    def _schema_proxy_options(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_FORWARD_TO_CLOUD,
                    default=defaults.get(
                        CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
                    ),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLE_CLOUD_DATA,
                    default=defaults.get(CONF_ENABLE_CLOUD_DATA, False),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_REFRESH_CONFIG_FROM_CLOUD,
                    default=defaults.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False),
                ): BooleanSelector(),
            }
        )

    def _get_defaults_for_user_step(self):
        return {
            CONF_NAME: self._name,
            CONF_DEVICE_ID: self._device_id,
            CONF_WEBHOOK_ID: self._webhook_id,
        }

    def _get_defaults_for_optional_step(self):
        return {
            CONF_IP_ADDRESS: self._host_ip,
            ONLY_ONE_IP: self._only_ip,
            NOTIFY_MIGRATION: self._notify_migration,
            CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
        }

    def _get_defaults_for_proxy_step(self):
        return {
            CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud,
            CONF_ENABLE_CLOUD_DATA: self._enable_cloud_data,
            CONF_REFRESH_CONFIG_FROM_CLOUD: self._refresh_cloud_data,
        }

    # ----------------------------------------
    # Reconfigure
    # ----------------------------------------
    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        if not entry:
            return self.async_abort(reason="entry_not_found")

        self._entry = entry

        self._name = entry.data.get(CONF_NAME)
        self._device_id = entry.data.get(CONF_DEVICE_ID)
        self._webhook_id = entry.data.get(CONF_WEBHOOK_ID)
        self._host_ip = entry.data.get(CONF_IP_ADDRESS)
        self._only_ip = entry.data.get(ONLY_ONE_IP, False)
        self._notify_migration = entry.data.get(NOTIFY_MIGRATION, False)
        self._enable_local_cloud_proxy = entry.data.get(
            CONF_ENABLE_LOCAL_CLOUD_PROXY, False
        )
        self._enable_forward_to_cloud = entry.data.get(
            CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
        )
        self._enable_cloud_data = entry.data.get(CONF_ENABLE_CLOUD_DATA, False)
        self._refresh_cloud_data = entry.data.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False)

        return await self.async_step_user(user_input)
