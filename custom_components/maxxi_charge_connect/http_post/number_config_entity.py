"""
NumberConfigEntity-Modul für MaxxiCharge-Integration in Home Assistant.

Dieses Modul stellt eine beschreibbare `NumberEntity` zur Verfügung, mit der konfigurierbare
Parameter des MaxxiCharge-Geräts via HTTP-POST gesetzt werden können.

Verwendet wird der DataUpdateCoordinator aus `hass.data[DOMAIN][entry.entry_id]["coordinator"]`.

Abhängigkeiten:
    - aiohttp
    - Home Assistant Core und Komponenten
    - Lokale Hilfsmodule: const, tools

"""

import logging
import aiohttp
from aiohttp import ClientConnectorError, ClientError

from homeassistant.core import HomeAssistant
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from ..const import DEVICE_INFO, DOMAIN  # pylint: disable=relative-beyond-top-level
from ..tools import as_float  # pylint: disable=relative-beyond-top-level

_LOGGER = logging.getLogger(__name__)


class NumberConfigEntity(NumberEntity):  # pylint: disable=abstract-method
    """Konfigurierbare NumberEntity für MaxxiCharge-Geräteeinstellungen.

    Diese Entität ermöglicht die Anzeige und Änderung eines konfigurierbaren Parameters
    auf dem MaxxiCharge-Gerät. Änderungen werden über eine HTTP-POST-Anfrage an das Gerät gesendet.

    Attribute:
        _rest_key (str): Der REST-Parametername, der an das Gerät gesendet wird.
        _value_key (str): Der Schlüssel zur Extraktion des Werts aus dem Koordinator.
        _ip (str): IP-Adresse des MaxxiCharge-Geräts.
        _coordinator: Der DataUpdateCoordinator mit aktuellen Gerätedaten.
    """

    _attr_has_entity_name = True

    # pylint: disable=too-many-positional-arguments,too-many-arguments
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        translation_key: str,
        rest_key: str,
        value_key: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str,
    ) -> None:
        """Initialisiert die NumberConfigEntity.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfigurationseintrag-Instanz.
            translation_key (str): Der Schlüssel zur Übersetzung der Entität.
            rest_key (str): Der Schlüsselname für den POST-Request.
            value_key (str): Der Schlüsselname zum Extrahieren des Werts aus Koordinator-Daten.
            min_value (float): Minimal erlaubter Wert.
            max_value (float): Maximal erlaubter Wert.
            step (float): Schrittweite für die Eingabe.
            unit (str): Einheit der Messgröße.

        """

        self._attr_mode = NumberMode.BOX
        self._entry = entry
        self._hass = hass
        self._ip = entry.data[CONF_IP_ADDRESS].strip()
        self._coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        self._rest_key = rest_key
        self._value_key = value_key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{self._coordinator.entry.entry_id}_{rest_key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = None  # Initial leer
        self._attr_entity_category = EntityCategory.CONFIG

        _LOGGER.debug("Wert: %s", as_float(self._coordinator.data.get(self._value_key)))

        if self._coordinator.data:
            self._attr_native_value = as_float(
                self._coordinator.data.get(self._value_key)
            )
        else:
            self._attr_native_value = None

    async def async_added_to_hass(self):
        """Registriert Callback bei Datenaktualisierung durch den Koordinator."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    def set_native_value(self, value: float) -> None:
        """Synchroner Wrapper für async_set_native_value."""
        self._hass.async_create_task(self.async_set_native_value(value))

    async def async_set_native_value(self, value: float) -> None:
        """Wert setzen und per REST an das Gerät senden."""
        self._attr_native_value = value
        await self._send_config_to_device(value)

    async def _send_config_to_device(self, value: float) -> None:
        """Sendet den Wert via HTTP-POST an das Gerät."""

        payload = f"{self._rest_key}={int(value)}"

        _LOGGER.debug("send data (%s, %s) to maxxicharge", self._value_key, payload)

        if not self._ip:
            _LOGGER.error("IP-Adresse ist nicht gesetzt")
            return

        # headers = {"Content-Type": "application/x-www-form-urlencoded"}
        url = f"http://{self._ip}/config"

        try:
            async with aiohttp.ClientSession() as session:
                # async with session.post(url, data=payload, headers=headers) as response:
                async with session.post(url, data=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error(
                            "Fehler beim Senden von %s = %s: %s",
                            self._rest_key,
                            value,
                            text,
                        )
                    text = await response.text()
                    # _LOGGER.warning("Antwort: %s", text)
            _LOGGER.debug("POST fertig")
            await self._coordinator.async_request_refresh()

        except ClientConnectorError as e:
            _LOGGER.error(
                "Verbindung zu MaxxiCharge (%s) fehlgeschlagen: %s", self._ip, e
            )
        except ClientError as e:
            _LOGGER.error(
                "HTTP-Fehler beim Senden von %s = %s: %s", self._rest_key, value, e
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.exception(
                "Unerwarteter Fehler bei %s = %s: %s", self._rest_key, value, e
            )

    @property
    def native_value(self):
        """Gibt den aktuellen Wert der Text-Entität zurück.

        Returns:
            str | None: Der extrahierte Wert aus dem Koordinator oder None,
                        falls keine Daten vorhanden sind.

        """
        _LOGGER.debug(
            "Value: %s", as_float(self._coordinator.data.get(self._value_key))
        )
        return (
            as_float(self._coordinator.data.get(self._value_key))
            if self._coordinator.data
            else None
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Gibt die Geräteinformationen zurück."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
        }
