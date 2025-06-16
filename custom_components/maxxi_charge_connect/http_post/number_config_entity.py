"""NumberEntity zur Konfiguration von MaxxiCharge-Geräten via REST.

Dieses Modul definiert die `NumberConfigEntity`, eine `NumberEntity`-Unterklasse
für Home Assistant, die beschreibbare Werte wie Ladegrenzen oder Schaltschwellen
über eine HTTP-POST-Anfrage an ein MaxxiCharge-Gerät überträgt.
"""

import logging
import aiohttp

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.config_entries import ConfigEntry
from aiohttp import ClientError, ClientConnectorError


_LOGGER = logging.getLogger(__name__)


class NumberConfigEntity(NumberEntity):  # pylint: disable=abstract-method
    """Beschreibbare NumberEntity für MaxxiCharge-Konfigurationsparameter.

    Diese Entität erlaubt das Setzen von numerischen Konfigurationswerten,
    die über einen HTTP-POST an das MaxxiCharge-Gerät gesendet werden.

    Attribute:
        _ip (str): IP-Adresse des MaxxiCharge-Geräts.
        _rest_key (str): Schlüssel für das zu setzende Konfigurationsfeld.
        _name_translation_key (str): Übersetzungsschlüssel für die Anzeige im UI.
        _attr_native_value (float | None): Der aktuell gesetzte Wert.

    """

    def __init__(
        self,
        entry: ConfigEntry,
        translation_key: str,
        key: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str,
    ) -> None:
        """Initialisiert die NumberConfigEntity.

        Args:
            entry (ConfigEntry): Die Konfigurationseinträge der Integration.
            translation_key (str): Übersetzungsschlüssel für die Anzeige im UI.
            key (str): Der Name des REST-Parameters.
            min_value (float): Der minimale gültige Wert.
            max_value (float): Der maximale gültige Wert.
            step (float): Schrittweite des Wertes.
            unit (str): Einheit des Wertes.

        """

        self._ip = entry.data[CONF_IP_ADDRESS].strip()
        self._rest_key = key
        self._name_translation_key = translation_key
        # self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{translation_key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = None  # Anfangswert

    def set_native_value(self, value: float) -> None:
        """Setzt synchron den neuen Wert und triggert das asynchrone Setzen.
           Linter-Zufriedenstellung, Home Assistant verwendet async_set_native_value

        Args:
            value (float): Der zu setzende Wert.

        """

        self.hass.async_create_task(self.async_set_native_value(value))

    async def async_set_native_value(self, value: float) -> None:
        """Wert setzen und per REST an das Gerät senden."""
        self._attr_native_value = value
        await self._send_config_to_device(value)

    async def _send_config_to_device(self, value: float) -> None:
        """Sendet den gegebenen Wert als Konfigurationsparameter via HTTP-POST.

        Args:
            value (float): Der Wert, der an das Gerät gesendet wird.

        Raises:
            ClientConnectorError: Falls keine Verbindung zum Gerät aufgebaut werden kann.
            ClientError: Bei allgemeinen HTTP-Fehlern.
            Exception: Bei allen anderen unerwarteten Fehlern.
            
        """

        if (self._ip):
            payload = f"{self._rest_key}={int(value)}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            url = f"http://{self._ip}/config"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=payload, headers=headers) as response:
                        if response.status != 200:
                            text = await response.text()
                            _LOGGER.error("Fehler beim Senden von %s = %s: %s", self._rest_key, value, text)
            except ClientConnectorError as e:
                _LOGGER.error("Verbindung zu MaxxiCharge (%s) fehlgeschlagen: %s", self._ip, e)
            except ClientError as e:
                _LOGGER.error("HTTP-Fehler beim Senden von %s = %s: %s", self._rest_key, value, e)
            except Exception as e:  # pylint: disable=broad-exception-caught # für unerwartete Fehler
                _LOGGER.exception("Unerwarteter Fehler bei %s = %s: %s", self._rest_key, value, e)
        else:
            _LOGGER.error("IP-Adresse ist nicht gesetzt.")
