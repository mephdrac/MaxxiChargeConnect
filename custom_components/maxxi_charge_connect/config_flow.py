"""Konfigurationsfluss für MaxxiChargeConnect mit Duplicate-Prüfung"""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import BooleanSelector, TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    CCU_V1,
    CCU_V2,
    CONF_CCU_VERSION,
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_ENABLE_MQTT_BROKER,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_REFRESH_CONFIG_FROM_CLOUD,
    CONF_TIMEOUT_RECEIVE,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    DEFAULT_TIMEOUT_RECEIVE,
    DOMAIN,
    NOTIFY_MIGRATION,
    ONLY_ONE_IP,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow für MaxxiChargeConnect mit Duplicate-Prüfung."""

    VERSION = 4
    MINOR_VERSION = 0

    _ccu_version: str | None = None

    reconfigure_supported = True

    _name: str | None = None
    _webhook_id: str | None = None
    _timeout_receive: int | None = DEFAULT_TIMEOUT_RECEIVE
    _device_id: str | None = None
    _host_ip: str | None = None
    _only_ip: bool = False
    _notify_migration: bool = False
    _enable_local_cloud_proxy: bool = False
    _enable_forward_to_cloud: bool = DEFAULT_ENABLE_FORWARD_TO_CLOUD
    _enable_cloud_data: bool = False
    _refresh_cloud_data: bool = False

    _entry: config_entries.ConfigEntry | None = None  # nur beim Reconfigure

    def __init__(self):
        self._enable_mqtt_broker = False
        self._mqtt_settings = {}

    async def async_step_mqtt(self, user_input=None):
        """Configure the shared, opt-in broker; never log credentials."""
        if not self._enable_mqtt_broker:
            return self._create_entry(entry=self._entry)

        others = [
            entry
            for entry in self._async_current_entries()
            if entry.data.get(CONF_ENABLE_MQTT_BROKER, False)
            and (self._entry is None or entry.entry_id != self._entry.entry_id)
        ]
        shared = others[0].data if others else {}
        defaults = self._mqtt_settings or {
            CONF_MQTT_PORT: shared.get(CONF_MQTT_PORT, 1883),
            CONF_MQTT_USERNAME: shared.get(CONF_MQTT_USERNAME, ""),
            CONF_MQTT_PASSWORD: shared.get(CONF_MQTT_PASSWORD, ""),
        }
        errors = {}
        if user_input is not None:
            settings = {
                CONF_MQTT_PORT: user_input[CONF_MQTT_PORT],
                CONF_MQTT_USERNAME: user_input[CONF_MQTT_USERNAME],
                CONF_MQTT_PASSWORD: user_input.get(CONF_MQTT_PASSWORD) or defaults.get(CONF_MQTT_PASSWORD, ""),
            }
            if not settings[CONF_MQTT_USERNAME].strip():
                errors[CONF_MQTT_USERNAME] = "required"
            if not settings[CONF_MQTT_PASSWORD]:
                errors[CONF_MQTT_PASSWORD] = "required"
            if shared and any(settings[key] != shared.get(key) for key in settings):
                errors["base"] = "mqtt_settings_conflict"
            if not errors:
                self._mqtt_settings = settings
                return self._create_entry(entry=self._entry)
            defaults = {**defaults, **settings}

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MQTT_PORT, default=defaults[CONF_MQTT_PORT]): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Required(CONF_MQTT_USERNAME, default=defaults[CONF_MQTT_USERNAME]): str,
                    vol.Optional(CONF_MQTT_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                }
            ),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Select CCU version."""

        if user_input is not None:
            self._ccu_version = user_input.get(CONF_CCU_VERSION, CCU_V1)

            if self._ccu_version == CCU_V1:
                return await self.async_step_v1()

            if self._ccu_version == CCU_V2:
                if self._entry is None:
                    self._timeout_receive = 30
                return await self.async_step_v2()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CCU_VERSION,
                        default=self._ccu_version or CCU_V1,
                    ): vol.In(
                        {
                            CCU_V1: "CCU V1",
                            CCU_V2: "CCU V2",
                        }
                    )
                }
            ),
        )

    async def async_step_v2(self, user_input=None):
        """Configure the CCU identity and select internal or existing HA MQTT."""
        errors = {}
        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._device_id = user_input[CONF_DEVICE_ID]
            self._enable_mqtt_broker = user_input.get(CONF_ENABLE_MQTT_BROKER, False)
            self._timeout_receive = user_input.get(CONF_TIMEOUT_RECEIVE, 30)
            if not self._name.strip():
                errors[CONF_NAME] = "required"
            if not self._device_id.strip() or any(char in self._device_id for char in "+#\x00"):
                errors[CONF_DEVICE_ID] = "invalid_device_id"
            for entry in self._async_current_entries():
                if entry.data.get(CONF_DEVICE_ID) == self._device_id and (
                    self._entry is None or entry.entry_id != self._entry.entry_id
                ):
                    errors[CONF_DEVICE_ID] = "device_exists"
            if not errors:
                if self._entry is None:
                    await self.async_set_unique_id(self._device_id)
                    self._abort_if_unique_id_configured()

                return await self.async_step_mqtt()

        return self.async_show_form(
            step_id="v2",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self._name or ""): str,
                    vol.Required(CONF_DEVICE_ID, default=self._device_id or ""): str,
                    vol.Optional(CONF_ENABLE_MQTT_BROKER, default=self._enable_mqtt_broker): BooleanSelector(),
                    vol.Required(CONF_TIMEOUT_RECEIVE, default=self._timeout_receive or 30): vol.All(
                        vol.Coerce(int), vol.Range(min=5)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_v1(self, user_input=None):  # für CCU v1
        """Configure CCU V1.

        Step 1: Pflichtfelder."""

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

            _LOGGER.debug("Defaults in user step: %s", defaults)

            if errors:
                return self.async_show_form(
                    step_id="v1",
                    data_schema=self._schema_user(defaults),
                    errors=errors,
                )

            if self._entry is None:
                await self.async_set_unique_id(self._device_id)
                self._abort_if_unique_id_configured()

            return await self.async_step_optional()

        return self.async_show_form(step_id="v1", data_schema=self._schema_user(defaults))

    async def async_step_optional(self, user_input=None):
        """Step 2: optionale Felder + Proxy aktivieren."""

        errors = {}
        defaults = self._get_defaults_for_optional_step()

        if user_input:
            self._host_ip = user_input.get(CONF_IP_ADDRESS)
            self._only_ip = user_input.get(ONLY_ONE_IP, False)
            self._timeout_receive = user_input.get(CONF_TIMEOUT_RECEIVE, DEFAULT_TIMEOUT_RECEIVE)
            self._notify_migration = user_input.get(NOTIFY_MIGRATION, False)
            self._enable_local_cloud_proxy = user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)

            # Pflichtfeldprüfung
            if not self._timeout_receive:
                errors["timeout_receive"] = "required"
            # Ende Pflichtfeldprüfung

            if errors:
                return self.async_show_form(
                    step_id="optional",
                    data_schema=self._schema_optional(defaults),
                    errors=errors,
                )

            if self._enable_local_cloud_proxy:
                return await self.async_step_proxy_options()

            return self._create_entry(entry=self._entry)

        return self.async_show_form(step_id="optional", data_schema=self._schema_optional(defaults))

    async def async_step_proxy_options(self, user_input=None):
        """Step 3: Proxy-Optionen."""

        defaults = self._get_defaults_for_proxy_step()

        if user_input:
            self._enable_forward_to_cloud = user_input.get(
                CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
            )
            self._enable_cloud_data = user_input.get(CONF_ENABLE_CLOUD_DATA, False)
            self._refresh_cloud_data = user_input.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False)
            return self._create_entry(entry=self._entry)

        return self.async_show_form(step_id="proxy_options", data_schema=self._schema_proxy_options(defaults))

    # ----------------------------------------
    # Entry erstellen / aktualisieren
    # ----------------------------------------
    def _create_entry(self, entry=None):
        data = {
            CONF_CCU_VERSION: self._ccu_version,
            CONF_NAME: self._name,
            CONF_DEVICE_ID: self._device_id or entry.data.get(CONF_DEVICE_ID),
            CONF_WEBHOOK_ID: self._webhook_id,
            CONF_TIMEOUT_RECEIVE: self._timeout_receive or DEFAULT_TIMEOUT_RECEIVE,
            CONF_IP_ADDRESS: self._host_ip or None,
            ONLY_ONE_IP: self._only_ip,
            NOTIFY_MIGRATION: self._notify_migration,
            CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
            CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud,
            CONF_ENABLE_CLOUD_DATA: self._enable_cloud_data,
            CONF_REFRESH_CONFIG_FROM_CLOUD: self._refresh_cloud_data,
        }
        data[CONF_ENABLE_MQTT_BROKER] = self._ccu_version == CCU_V2 and self._enable_mqtt_broker
        if data[CONF_ENABLE_MQTT_BROKER]:
            data.update(self._mqtt_settings)

        if entry is not None:
            self.hass.config_entries.async_update_entry(entry, data=data, title=self._name)
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
                vol.Required(CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")): str,
                vol.Required(CONF_WEBHOOK_ID, default=defaults.get(CONF_WEBHOOK_ID, "")): str,
            }
        )

    def _schema_optional(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Optional(CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, "")): str,
                vol.Optional(ONLY_ONE_IP, default=defaults.get(ONLY_ONE_IP, False)): BooleanSelector(),
                vol.Required(
                    CONF_TIMEOUT_RECEIVE,
                    default=defaults.get(CONF_TIMEOUT_RECEIVE, DEFAULT_TIMEOUT_RECEIVE),
                ): int,
                vol.Optional(NOTIFY_MIGRATION, default=defaults.get(NOTIFY_MIGRATION, False)): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLE_LOCAL_CLOUD_PROXY,
                    default=defaults.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY),
                ): BooleanSelector(),
            }
        )

    def _schema_proxy_options(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_FORWARD_TO_CLOUD,
                    default=defaults.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD),
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
            CONF_TIMEOUT_RECEIVE: self._timeout_receive,
            NOTIFY_MIGRATION: self._notify_migration,
            CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
        }

    def _get_defaults_for_proxy_step(self):
        return {
            CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud,
            CONF_ENABLE_CLOUD_DATA: self._enable_cloud_data,
            CONF_REFRESH_CONFIG_FROM_CLOUD: self._refresh_cloud_data,
        }

    async def async_step_reconfigure(self, user_input=None):
        """Reconfigure."""

        entry = self._get_reconfigure_entry()
        if not entry:
            return self.async_abort(reason="entry_not_found")

        self._entry = entry
        self._ccu_version = entry.data.get(CONF_CCU_VERSION, CCU_V1)
        self._enable_mqtt_broker = entry.data.get(CONF_ENABLE_MQTT_BROKER, False)
        self._mqtt_settings = (
            {
                CONF_MQTT_PORT: entry.data.get(CONF_MQTT_PORT, 1883),
                CONF_MQTT_USERNAME: entry.data.get(CONF_MQTT_USERNAME, ""),
                CONF_MQTT_PASSWORD: entry.data.get(CONF_MQTT_PASSWORD, ""),
            }
            if entry.data.get(CONF_MQTT_PASSWORD)
            else {}
        )

        self._name = entry.data.get(CONF_NAME)
        self._device_id = entry.data.get(CONF_DEVICE_ID)
        self._webhook_id = entry.data.get(CONF_WEBHOOK_ID)
        self._timeout_receive = entry.data.get(CONF_TIMEOUT_RECEIVE)
        self._host_ip = entry.data.get(CONF_IP_ADDRESS)
        self._only_ip = entry.data.get(ONLY_ONE_IP, False)
        self._notify_migration = entry.data.get(NOTIFY_MIGRATION, False)
        self._enable_local_cloud_proxy = entry.data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)
        self._enable_forward_to_cloud = entry.data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)
        self._enable_cloud_data = entry.data.get(CONF_ENABLE_CLOUD_DATA, False)
        self._refresh_cloud_data = entry.data.get(CONF_REFRESH_CONFIG_FROM_CLOUD, False)

        _LOGGER.debug(
            "Reconfigure internal state: %s",
            {
                "name": self._name,
                "device_id": self._device_id,
                "webhook_id": self._webhook_id,
                "host_ip": self._host_ip,
                "only_ip": self._only_ip,
                "notify_migration": self._notify_migration,
                "enable_local_cloud_proxy": self._enable_local_cloud_proxy,
                "enable_forward_to_cloud": self._enable_forward_to_cloud,
                "enable_cloud_data": self._enable_cloud_data,
                "refresh_cloud_data": self._refresh_cloud_data,
                "timeout_receive": self._timeout_receive,
            },
        )
        if self._ccu_version == CCU_V2:
            return await self.async_step_v2(user_input)
        return await self.async_step_v1(user_input)

    def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:
        return (
            isinstance(other_flow, MaxxiChargeConnectConfigFlow)
            and self._webhook_id == other_flow._webhook_id  # pylint: disable=protected-access
            and self._device_id == other_flow._device_id  # pylint: disable=protected-access
        )  # pylint: disable=protected-access
