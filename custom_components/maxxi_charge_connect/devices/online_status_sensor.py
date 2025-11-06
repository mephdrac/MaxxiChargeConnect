"""Sensor-Entity zur Anzeige, wann die letzen Messdaten gekommen sind.

Die Klasse nutzt Home Assistants Dispatcher-System, um auf neue Sensordaten zu reagieren.
"""

from datetime import UTC, datetime
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import (
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    DEVICE_INFO,
    DOMAIN,
    PROXY_ERROR_DEVICE_ID,
    PROXY_STATUS_EVENTNAME,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
)  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class OnlineStatusSensor(BinarySensorEntity):
    """SensorEntity für die aktuelle Uptime (uptime).

    Diese Entität zeigt umgerechnet in Tage, Stunden, Minuten und Sekunden an.
    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "OnlineStatusSensor"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialisiert den LastMessageSensor.

        Args:
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz für diese Integration.

        """
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_online_status_sensor"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = False

        self._unsub_update = None
        self._unsub_stale = None
        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    async def async_added_to_hass(self):
        """HA informiert uns, dass der Sensor hinzugefügt wurde."""
        await super().async_added_to_hass()

        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]

        update_signal = entry_data[WEBHOOK_SIGNAL_UPDATE]
        stale_signal = entry_data[WEBHOOK_SIGNAL_STATE]

        self._attr_available = True  # bis erstes gültiges Update kommt
        self._attr_is_on = False

        if self._enable_cloud_data:
            _LOGGER.info("Daten kommen vom Proxy")
            self.hass.bus.async_listen(
                PROXY_STATUS_EVENTNAME, self.async_update_from_event
            )
        else:
            # Dispatcher abonnieren
            self._unsub_update = async_dispatcher_connect(
                self.hass, update_signal, self._wrapper_update
            )

        self._unsub_stale = async_dispatcher_connect(
            self.hass, stale_signal, self._wrapper_stale
        )

        # # letzten Zustand wiederherstellen
        # old_state = await self.async_get_last_state()
        # if old_state is not None and old_state.state not in (>
        #     STATE_UNAVAILABLE,
        #     "unknown",
        #     None,
        # ):
        #     try:
        #         self._attr_native_value = float(old_state.state)
        #         self._attr_available = True
        #     except Exception:
        #         pass

    async def async_will_remove_from_hass(self):
        """Abmelden beim Dispatcher."""
        if hasattr(self, "_unsub_update"):
            self._unsub_update()
        if hasattr(self, "_unsub_stale"):
            self._unsub_stale()

    async def _wrapper_update(self, data: dict):
        """Ablauf bei einem eingehenden Update-Event."""
        try:
            await self.handle_update(data)
            self._attr_available = True
            self._attr_is_on = True
            self.async_write_ha_state()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fehler im Sensor %s beim Update: %s", self.__class__.__name__, err
            )

    async def _wrapper_stale(self, _):
        """Ablauf, wenn das Watchdog-Event 'stale' gesendet wird."""
        await self.handle_stale()
        self.async_write_ha_state()

    async def handle_stale(self):
        """Standardverhalten: Sensor auf 'unavailable' setzen."""
        # self._attr_available = False
        self._attr_is_on = False
        self.async_write_ha_state()

    async def handle_update(self, data):
        """Verarbeitet neue Webhook-Daten und aktualisiert den Sensorzustand.

        Und prüft auf Plausibilität.

        Args:
            data (dict): Die per Webhook empfangenen Sensordaten.

        """
        try:
            uptime_ms = int(data.get("uptime", 0))

            now_utc = datetime.now(tz=UTC)
            self._attr_is_on = True

            seconds_total = uptime_ms / 1000

            # lesbares Format als extra attribute
            days, remainder = divmod(int(seconds_total), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            self._attr_extra_state_attributes = {
                "received": now_utc.isoformat(),
                "uptime": f"{days}d {hours}h {minutes}m {seconds}s",
                "raw_ms": uptime_ms,
                "─────────────": "────────────────────────",
                "data:": data,
            }
            self.async_write_ha_state()

        except ValueError as e:
            _LOGGER.warning("Uptime-Wert ungültig: %s", e)

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self.handle_update(json_data)

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
