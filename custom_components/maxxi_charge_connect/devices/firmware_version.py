"""TextEntity zur Anzeige der Firmware-Version eines Batteriesystems in Home Assistant.

Diese Entität zeigt die aktuelle Firmware-Version an, die über einen Webhook empfangen wird.
Sie ist als diagnostische Entität kategorisiert.
"""

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252


class FirmwareVersion(TextEntity):
    """TextEntity zur Anzeige der Firmware-Version eines Geräts."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert die Entity für die Firmware-Version.

        Args:
            entry (ConfigEntry): Der Konfigurationseintrag der Integration.

        """
        self._unsub_dispatcher = None
        self._entry = entry
        self._attr_name = "Firmware Version"
        self._attr_unique_id = f"{entry.entry_id}_firmware_version"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        """Wird beim Hinzufügen zur Home Assistant-Instanz aufgerufen.

        Registriert sich beim Dispatcher, um auf eingehende Webhook-Daten zu reagieren.
        """

        signal_sensor = f"{DOMAIN}_{self._entry.data[CONF_WEBHOOK_ID]}_update_sensor"

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal_sensor, self._handle_update
        )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal_sensor, self._handle_update)
        )

    async def async_will_remove_from_hass(self):
        """Wird beim Entfernen der Entity aus Home Assistant aufgerufen.

        Hebt die Dispatcher-Registrierung auf.
        """

        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    async def _handle_update(self, data):
        """Verarbeitet empfangene Webhook-Daten und aktualisiert die Firmware-Version.

        Args:
            data (dict): Die empfangenen Daten vom Webhook.

        """

        value = str(data.get("firmwareVersion", "unknown"))
        self._attr_native_value = value
        self.async_write_ha_state()

    def set_value(self, value):
        self._attr_native_value = value

    @property
    def device_info(self):
        """Liefert die Geräteinformationen für diese Sensor-Entity.

        Returns:
            dict: Ein Dictionary mit Informationen zur Identifikation
                  des Geräts in Home Assistant, einschließlich:
                  - identifiers: Eindeutige Identifikatoren (Domain und Entry ID)
                  - name: Anzeigename des Geräts
                  - manufacturer: Herstellername
                  - model: Modellbezeichnung

        """

        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
