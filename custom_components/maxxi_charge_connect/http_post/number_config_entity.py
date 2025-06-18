import logging
import aiohttp
from aiohttp import ClientConnectorError, ClientError

from homeassistant.core import HomeAssistant
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later

from ..const import DEVICE_INFO, DOMAIN
from ..tools import as_float

_LOGGER = logging.getLogger(__name__)


class NumberConfigEntity(NumberEntity):  # pylint: disable=abstract-method
    """Beschreibbare NumberEntity für MaxxiCharge-Konfigurationsparameter."""

    _attr_has_entity_name = True

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
        """Initialisiert die NumberConfigEntity."""

        self._attr_mode = NumberMode.BOX
        self._entry = entry
        self._hass = hass
        self._ip = entry.data[CONF_IP_ADDRESS].strip()
        self._coordinator = hass.data[DOMAIN]["coordinator"]
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
        except Exception as e:
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
