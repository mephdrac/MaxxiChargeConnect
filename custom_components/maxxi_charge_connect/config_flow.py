"""Konfigurations-Flow für die MaxxiChargeConnect Integration.

Dieses Modul implementiert den Konfigurations-Flow für die Home Assistant Integration
"MaxxiChargeConnect". Es ermöglicht die Einrichtung und Neukonfiguration eines
ConfigEntry, inklusive:

- Abfrage von Name, Webhook-ID, IP-Adresse und IP-Whitelist-Option im Setup-Dialog.
- Unterstützung eines Reconfigure-Flows zur Änderung bestehender Einträge.
- Migration von Version 1 zu Version 2 der Konfigurationseinträge.

Der Flow validiert keine Eingaben, sondern speichert sie zur weiteren Nutzung
in der Integration.

Typischerweise wird dieser Flow vom Home Assistant Framework automatisch
aufgerufen, wenn der Nutzer die Integration hinzufügt oder neu konfiguriert.

"""

import logging
from typing import Any

import voluptuous as vol


from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME, CONF_WEBHOOK_ID
from homeassistant.helpers.selector import BooleanSelector
from .migration.migration_from_yaml import MigrateFromYaml

from .webhook import async_unregister_webhook

from .const import DOMAIN, ONLY_ONE_IP, NOTIFY_MIGRATION, CONF_REAL_CLOUD_URL, \
                    CONF_ENABLE_LOCAL_CLOUD_PROXY, DEFAULT_REAL_CLOUD_URL, \
                    CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD

_LOGGER = logging.getLogger(__name__)


# pylint: disable=W0237
class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die MaxxiChargeConnect Integration.

    Unterstützt den Standard-Setup-Flow sowie einen Reconfigure-Flow,
    um bestehende Einträge zu ändern.

    Attributes:
        VERSION (int): Versionsnummer der Config-Flow-Datenstruktur.
        reconfigure_supported (bool): Ob der Reconfigure-Flow aktiviert ist.

    """

    VERSION = 3
    MINOR_VERSION = 1
    reconfigure_supported = True  # <- Aktiviert den Reconfigure-Flow

    _name = None
    _webhook_id: str = ""
    _host_ip = None
    _only_ip = False
    _notify_migration = False
    _enable_local_cloud_proxy = False
    _real_cloud_url = DEFAULT_REAL_CLOUD_URL
    _enable_forward_to_cloud =DEFAULT_ENABLE_FORWARD_TO_CLOUD

    @property
    def webhook_id(self) -> str:
        """Öffentlicher Zugriff auf _webhook_id."""
        return self._webhook_id

    async def async_step_user(self, user_input=None):
        """Erster Schritt des Setup-Flows, der die Nutzereingaben abfragt.

        Args:
            user_input (dict | None): Vom Benutzer eingegebene Konfigurationsdaten.

        Returns:
            FlowResult: Nächster Schritt oder Abschluss des Flows mit neuem Eintrag.

        """

        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._webhook_id = user_input[CONF_WEBHOOK_ID]
            self._host_ip = user_input.get(CONF_IP_ADDRESS, None)
            self._only_ip = user_input.get(ONLY_ONE_IP, False)
            self._notify_migration = user_input.get(NOTIFY_MIGRATION, False)
            self._enable_local_cloud_proxy = user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)
            self._real_cloud_url = user_input.get(CONF_REAL_CLOUD_URL, DEFAULT_REAL_CLOUD_URL)
            self._enable_forward_to_cloud = user_input.get(CONF_ENABLE_FORWARD_TO_CLOUD, DEFAULT_ENABLE_FORWARD_TO_CLOUD)

            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_NAME: self._name,
                    CONF_IP_ADDRESS: self._host_ip,
                    ONLY_ONE_IP: self._only_ip,
                    NOTIFY_MIGRATION: self._notify_migration,
                    CONF_ENABLE_LOCAL_CLOUD_PROXY: self._enable_local_cloud_proxy,
                    CONF_REAL_CLOUD_URL: self._real_cloud_url,
                    CONF_ENABLE_FORWARD_TO_CLOUD: self._enable_forward_to_cloud
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_WEBHOOK_ID): str,
                    vol.Optional(CONF_IP_ADDRESS, default=""): str,
                    vol.Optional(ONLY_ONE_IP, default=False): BooleanSelector(),
                    vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=True): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=True): BooleanSelector(),
                    vol.Optional(CONF_REAL_CLOUD_URL, default=DEFAULT_REAL_CLOUD_URL): str,

                }
            ),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Flow-Schritt für die Neukonfiguration eines bestehenden Eintrags.

        Args:
            user_input (dict | None): Neue Konfigurationsdaten vom Benutzer.

        Returns:
            FlowResult: Nächster Schritt oder Abschluss des Reconfigure-Flows.

        """

        entry = self._get_reconfigure_entry()

        if user_input is not None:
            if user_input.get(NOTIFY_MIGRATION):
                migrator = MigrateFromYaml(self.hass, entry)
                await migrator.async_notify_possible_migration()

            old_webhook_id = entry.data.get(CONF_WEBHOOK_ID)
            new_data = {                
                CONF_WEBHOOK_ID: user_input[CONF_WEBHOOK_ID],
                CONF_IP_ADDRESS: user_input.get(CONF_IP_ADDRESS, ""),
                ONLY_ONE_IP: user_input.get(ONLY_ONE_IP, False),
                CONF_ENABLE_LOCAL_CLOUD_PROXY: user_input.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False),
                CONF_REAL_CLOUD_URL: user_input.get(CONF_REAL_CLOUD_URL, DEFAULT_REAL_CLOUD_URL),
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
                    # vol.Required(CONF_NAME, default=current_data.get(CONF_NAME, "")): str,
                    vol.Required(
                        CONF_WEBHOOK_ID, default=current_data.get(CONF_WEBHOOK_ID, "")
                    ): str,
                    vol.Optional(
                        CONF_IP_ADDRESS, default=current_data.get(CONF_IP_ADDRESS, "")
                    ): str,
                    vol.Optional(
                        ONLY_ONE_IP, default=current_data.get(ONLY_ONE_IP, False)
                    ): BooleanSelector(),
                    vol.Optional(NOTIFY_MIGRATION, default=False): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_LOCAL_CLOUD_PROXY, default=current_data.get(CONF_ENABLE_LOCAL_CLOUD_PROXY, False)): BooleanSelector(),
                    vol.Optional(CONF_ENABLE_FORWARD_TO_CLOUD, default=current_data.get(CONF_ENABLE_FORWARD_TO_CLOUD, False)): BooleanSelector(),
                    vol.Optional(CONF_REAL_CLOUD_URL, default=current_data.get(CONF_REAL_CLOUD_URL, DEFAULT_REAL_CLOUD_URL)): str,
                }
            ),
        )

    def is_matching(self, other: config_entries.ConfigFlow) -> bool:
        """Vergleicht, ob dieser Flow einem bestehenden Flow entspricht."""
        if not isinstance(other, MaxxiChargeConnectConfigFlow):
            return False
        return self.webhook_id == other.webhook_id
