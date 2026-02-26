"""Basisklasse für alle Sensoren der MaxxiChargeConnect-Integration.

Diese Klasse:
- kümmert sich um Timeout/Stale-Handling
- empfängt automatische Dispatcher-Signale (UPDATE + STALE)
- stellt ein einheitliches Vererbungsmodell bereit
- nutzt RestoreEntity, um Werte nach Neustart zu behalten
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity


from ..const import (
    DEVICE_INFO,
    CONF_DEVICE_ID,
    CONF_ENABLE_CLOUD_DATA,
    DOMAIN,
    PROXY_ERROR_DEVICE_ID,
    PROXY_STATUS_EVENTNAME,
    HTTP_SCAN_EVENTNAME,
    WEBHOOK_SIGNAL_STATE,
    WEBHOOK_SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


class BaseWebhookSensor(RestoreEntity, SensorEntity):
    """Abstrakte Basisklasse für MaxxiCharge-Webhook-Sensoren.

    Abgeleitete Klassen müssen implementieren:
        async def handle_update(self, data: dict):
            -> Verarbeitung normaler Webhook-Daten

    Optional:
        async def handle_stale(self):
            -> Optional überschreibbar, default: Sensor unavailable
    """

    # Für die UI standardmäßig aktiviert
    _attr_entity_registry_enabled_default = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Basiskonstruktor für Sensoren.

        Args:
            hass: Home Assistant Instanz
            entry: ConfigEntry
            name: Anzeigename des Sensors
            unique_id: Eindeutige ID für HA
        """
        self._after_stale = True
        self._entry = entry
        self._attr_available = False  # bis erstes gültiges Update kommt

        self._unsub_update = None
        self._unsub_stale = None

        self._enable_cloud_data = self._entry.data.get(CONF_ENABLE_CLOUD_DATA, False)

    #
    # ---- HA Lifecycle ----
    #

    async def async_added_to_hass(self):
        """HA informiert uns, dass der Sensor hinzugefügt wurde."""
        await super().async_added_to_hass()

        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]

        update_signal = entry_data[WEBHOOK_SIGNAL_UPDATE]
        stale_signal = entry_data[WEBHOOK_SIGNAL_STATE]

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

        # letzten Zustand wiederherstellen
        old_state = await self.async_get_last_state()
        if old_state is not None and old_state.state not in (
            STATE_UNAVAILABLE,
            "unknown",
            None,
        ):
            try:
                # Versuch, den Wert basierend auf dem Sensortyp wiederherzustellen
                restored_value = self._restore_state_value(old_state.state)
                if restored_value is not None:
                    self._attr_native_value = restored_value
                    self._attr_available = True
                    _LOGGER.debug(
                        "Sensor %s: Zustand wiederhergestellt: %s",
                        self.__class__.__name__, restored_value
                    )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Sensor %s: Konnte Zustand nicht wiederherstellen: %s",
                    self.__class__.__name__, err
                )

    async def async_will_remove_from_hass(self):
        """Abmelden beim Dispatcher."""
        if hasattr(self, "_unsub_update"):
            self._unsub_update()
        if hasattr(self, "_unsub_stale"):
            self._unsub_stale()

    #
    # ---- Dispatcher-Wrapper ----
    #

    async def async_update_from_event(self, event: Event):
        """Aktualisiert Sensor von Proxy-Event."""

        _LOGGER.debug("Sensor(async_update_from_event) %s, %s: Event empfangen: %s", self.__class__.__name__, event.event_type, event)

        # HTTP-Scan Events ignorieren - diese haben keine Batterie-Daten
        if event.event_type == HTTP_SCAN_EVENTNAME:
            return

        json_data = event.data.get("payload", {})

        if json_data.get(PROXY_ERROR_DEVICE_ID) == self._entry.data.get(CONF_DEVICE_ID):
            await self._wrapper_update(json_data)

    async def check_valid(self, data: dict) -> bool:
        """Prüft, ob die empfangenen Daten gültig sind."""

        _LOGGER.debug("Sensor(check_valid) %s: Daten empfangen: %s", self.__class__.__name__, data)

        send_count = data.get("sendCount")
        device_id = data.get("deviceId")
        pccu = data.get("Pccu")
        batteries_info = data.get("batteriesInfo")

        if send_count is None:
            _LOGGER.error("Sensor(check_valid) %s: sendCount nicht gefunden", self.__class__.__name__)
            return False

        if device_id is None:
            _LOGGER.error("Sensor(check_valid) %s: deviceID nicht gefunden", self.__class__.__name__)
            return False

        if pccu is None:
            _LOGGER.error("Sensor(check_valid) %s: Pccu nicht gefunden", self.__class__.__name__)
            return False

        if batteries_info is None:
            _LOGGER.error("Sensor(check_valid) %s: batteriesInfo nicht gefunden", self.__class__.__name__)
            return False

        return True

    async def _wrapper_update(self, data: dict):
        """Ablauf bei einem eingehenden Update-Event."""
        try:
            _LOGGER.debug("Sensor(_wrapper_update) %s: Update empfangen: %s", self.__class__.__name__, data)

            if not await self.check_valid(data):
                return

            old_value = self._attr_native_value
            await self.handle_update(data)
            # Nur aktualisieren, wenn sich der Wert tatsächlich geändert hat oder zuvor ein Stale war
            if old_value != self._attr_native_value or self._after_stale:
                _LOGGER.debug("Sensor %s: Wert aktualisiert: %s", self.__class__.__name__, self._attr_native_value)
                self._attr_available = True
                self._after_stale = False
                self.async_write_ha_state()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fehler im Sensor %s beim Update: %s", self.__class__.__name__, err
            )

    async def _wrapper_stale(self, _):
        """Ablauf, wenn das Watchdog-Event 'stale' gesendet wird."""
        self._after_stale = True
        await self.handle_stale()
        self.async_write_ha_state()

    #
    # ---- Methoden für Kinderklassen ----
    #

    async def handle_update(self, data: dict):
        """Diese Methode MUSS in Kindklassen überschrieben werden.

        Args:
            data: JSON-Inhalt des Webhooks

        """
        raise NotImplementedError("Kindklassen müssen handle_update() implementieren")

    async def handle_stale(self):
        """Standardverhalten: Sensor auf 'unavailable' setzen."""
        self._attr_available = False
        self._attr_state = STATE_UNKNOWN
        self.async_write_ha_state()

    def _restore_state_value(self, state_str: str):
        """Stellt den Zustand basierend auf dem Sensortyp wieder her.
        Args:
            state_str: Der gespeicherte Zustand als String
        Returns:
            Der wiederhergestellte Wert im korrekten Typ oder None bei Fehler
        """
        # Standard: Versuch float-Konvertierung (für die meisten Sensoren)
        try:
            return float(state_str)
        except (ValueError, TypeError):
            pass

        # Wenn nichts passt, None zurückgeben
        return None

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
