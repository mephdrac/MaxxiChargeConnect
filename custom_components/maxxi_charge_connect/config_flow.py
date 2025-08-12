"""Konfigurationsfluss für das Maxxicharge Gerät"""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import BooleanSelector
from homeassistant.helpers import issue_registry as ir

from .migration.migration_from_yaml import MigrateFromYaml
from .webhook import async_unregister_webhook
from .const import (
    DOMAIN,
    ONLY_ONE_IP,
    NOTIFY_MIGRATION,
    CONF_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_FORWARD_TO_CLOUD,
    DEFAULT_ENABLE_LOCAL_CLOUD_PROXY,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für MaxxiChargeConnect."""

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
        """Liefert die Webhook_id zurück"""
        return self._webhook_id

    async def async_step_user(self, user_input=None):
        """Erster Setup-Schritt mit Validierung der device_id."""
        errors = {}

        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID)
            if not device_id or device_id.strip() == "":
                errors["device_id"] = "required"  # Schlüssel für Fehlermeldung

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_user_schema(user_input),
                    errors=errors,
                )

            # Wenn alles okay, dann Werte speichern
            self._store_user_input(user_input)

            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_NAME: self._name,
                    CONF_DEVICE_ID: device_id.strip(),  # Auf jeden Fall sauber
                    CONF_IP_ADDRESS: self._host_ip,
                    ONLY_ONE_IP: self._only_ip,
                    NOTIFY_MIGRATION: self._notify_migration,
                    CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
                    CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud,
                },
            )

        # Zeige Formular beim ersten Laden oder bei Fehlern
        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_schema()
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Reconfigure-Schritt."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            if not user_input.get(CONF_DEVICE_ID):
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(entry.data),
                    errors={"device_id": "required"},
                )

            if user_input.get(NOTIFY_MIGRATION):
                migrator = MigrateFromYaml(self.hass, entry)
                await migrator.async_notify_possible_migration()

            old_webhook_id = entry.data.get(CONF_WEBHOOK_ID)
            self._abort_if_unique_id_mismatch()

            await async_unregister_webhook(self.hass, entry, old_webhook_id)

            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_WEBHOOK_ID: user_input[CONF_WEBHOOK_ID],
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                    CONF_IP_ADDRESS: user_input.get(CONF_IP_ADDRESS, ""),
                    ONLY_ONE_IP: user_input.get(ONLY_ONE_IP, False),
                    CONF_ENABLE_LOCAL_CLOUD_PROXY: user_input.get(
                        CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY
                    ),
                    CONF_ENABLE_FORWARD_TO_CLOUD: user_input.get(
                        CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD
                    ),
                },
            )

        return self.async_show_form(
            step_id="reconfigure", data_schema=self._get_reconfigure_schema(entry.data)
        )

    async def async_step_fix_device_id(self, user_input: dict[str, Any] | None = None):
        """Extra-Flow, um fehlende device_id nachzutragen."""

        config_entry_id = self.context.get("config_entry_id")
        if not isinstance(config_entry_id, str):
            # Hier Fehler werfen oder abbrechen
            return self.async_abort(reason="missing_config_entry_id")

        entry = self.hass.config_entries.async_get_entry(config_entry_id)

        if not entry:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={CONF_DEVICE_ID: user_input[CONF_DEVICE_ID]},
            )

        return self.async_show_form(
            step_id="fix_device_id",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_ID, default=""): str}
            ),
        )

    async def async_step_import(self, user_input=None):
        """Import aus YAML."""
        return await self.async_step_user(user_input)

    def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:
        return isinstance(other_flow, MaxxiChargeConnectConfigFlow) and self.webhook_id == other_flow.webhook_id

    # -------------------------------------------------------
    # Hilfsfunktionen
    # -------------------------------------------------------

    def _get_user_schema(self, defaults=None):
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
                vol.Required(CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")): str,
                vol.Required(CONF_WEBHOOK_ID, default=defaults.get(CONF_WEBHOOK_ID, "")): str,
                vol.Optional(CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, "")): str,
                vol.Optional(ONLY_ONE_IP, default=defaults.get(ONLY_ONE_IP, False)): BooleanSelector(),
                vol.Optional(NOTIFY_MIGRATION, default=defaults.get(NOTIFY_MIGRATION, False)): BooleanSelector(),
                vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=defaults.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY)): BooleanSelector(),
                vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=defaults.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)): BooleanSelector(),
            }
        )

    def _get_reconfigure_schema(self, current_data):
        return vol.Schema(
            {
                vol.Required(CONF_WEBHOOK_ID, default=current_data.get(CONF_WEBHOOK_ID, "")): str,
                vol.Required(CONF_DEVICE_ID, default=current_data.get(CONF_DEVICE_ID, "")): str,
                vol.Optional(CONF_IP_ADDRESS, default=current_data.get(CONF_IP_ADDRESS, "")): str,
                vol.Optional(ONLY_ONE_IP, default=current_data.get(ONLY_ONE_IP, False)): BooleanSelector(),
                vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=current_data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_ENABLE_LOCAL_CLOUD_PROXY)): BooleanSelector(),
                vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=current_data.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)): BooleanSelector(),
            }
        )

    def _store_user_input(self, user_input):
        self._name = user_input[CONF_NAME]
        self._device_id = user_input[CONF_DEVICE_ID]
        self._webhook_id = user_input[CONF_WEBHOOK_ID]
        self._host_ip = user_input.get(CONF_IP_ADDRESS, None)
        self._only_ip = user_input.get(ONLY_ONE_IP, False)
        self._notify_migration = user_input.get(NOTIFY_MIGRATION, False)
        self._enable_local_cloud_proxy = user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)
        self._enable_forward_to_cloud = user_input.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)


# -------------------------------------------------------
# Repair-Issue bei fehlender device_id
# -------------------------------------------------------

async def async_check_device_id_and_create_issue(hass, entry):
    """Prüft device_id und erstellt Repair-Issue falls nötig."""
    if not entry.data.get(CONF_DEVICE_ID):
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"missing_device_id_{entry.entry_id}",
            is_fixable=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key="missing_device_id",
            data={"config_entry_id": entry.entry_id},
        )
