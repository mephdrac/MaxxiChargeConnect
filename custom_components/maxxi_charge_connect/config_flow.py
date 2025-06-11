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

from .const import DOMAIN, ONLY_ONE_IP

_LOGGER = logging.getLogger(__name__)


class MaxxiChargeConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die MaxxiChargeConnect Integration.

    Unterstützt den Standard-Setup-Flow sowie einen Reconfigure-Flow,
    um bestehende Einträge zu ändern.

    Attributes:
        VERSION (int): Versionsnummer der Config-Flow-Datenstruktur.
        reconfigure_supported (bool): Ob der Reconfigure-Flow aktiviert ist.

    """

    VERSION = 2
    reconfigure_supported = True  # <- Aktiviert den Reconfigure-Flow

    _name = None
    _webhook_id = None
    _host_ip = None
    _only_ip = False

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
            self._host_ip = user_input[CONF_IP_ADDRESS]
            self._only_ip = user_input[ONLY_ONE_IP]

            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_NAME: self._name,
                    CONF_IP_ADDRESS: self._host_ip,
                    ONLY_ONE_IP: self._only_ip,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_WEBHOOK_ID): str,
                    vol.Optional(CONF_IP_ADDRESS): str,
                    vol.Optional(ONLY_ONE_IP, default=False): BooleanSelector(),
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
            new_data = {
                # CONF_NAME: user_input[CONF_NAME],
                CONF_WEBHOOK_ID: user_input[CONF_WEBHOOK_ID],
                CONF_IP_ADDRESS: user_input.get(CONF_IP_ADDRESS, ""),
                ONLY_ONE_IP: user_input.get(ONLY_ONE_IP, False),
            }

            self._abort_if_unique_id_mismatch()

            return self.async_update_reload_and_abort(
                entry,
                data_updates=new_data,
                title=user_input[CONF_NAME],
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
                }
            ),
        )

    async def async_migrate_entry(self):
        """Migration eines Config-Eintrags von Version 1 auf Version 2.

        Args:
            hass (HomeAssistant): Home Assistant Instanz.
            config_entry (ConfigEntry): Zu migrierender Konfigurationseintrag.

        Returns:
            bool: True, falls Migration durchgeführt wurde, sonst False.

        """

        if self.config_entry.version == 1:
            new_data = {**self.config_entry.data}
            self.config_entry.version = 2
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            return True
        return False
