"""Coordinator-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert die Klasse MaxxiDataUpdateCoordinator, die regelmäßig
eine Web-Oberfläche per HTTP abruft, HTML parst und definierte Werte extrahiert,
um sie als Sensordaten in Home Assistant bereitzustellen.
"""

import logging
from datetime import timedelta

# import asyncio
import aiohttp
import async_timeout
from bs4 import BeautifulSoup
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # z.B. alle 30 Sekunden aktualisieren


class MaxxiDataUpdateCoordinator(DataUpdateCoordinator):
    """Koordinator zur zyklischen Abfrage und Extraktion von HTML-Werten für MaxxiChargeConnect."""

    def __init__(self, hass: HomeAssistant, entry, sensor_list) -> None:
        """Initialisiert den UpdateCoordinator.

        Args:
            hass (HomeAssistant): Die Home Assistant Instanz.
            entry (ConfigEntry): Die Konfiguration des Integrations-Eintrags.
            sensorList (List[Tuple[str, str]]): Liste von Sensor-Schlüsseln 
                    und zugehörigen HTML-Labels,
                    z.B. [("PowerMeterIp", "Messgerät IP:")]

        """

        super().__init__(
            hass,
            _LOGGER,
            name="maxxi_charge_connect",
            update_interval=SCAN_INTERVAL,
        )

        self._sensor_list = sensor_list
        self.entry = entry
        self._resource = entry.data[CONF_IP_ADDRESS].strip()

        if self._resource:
            if not self._resource.startswith(("http://", "https://")):
                self._resource = f"http://{self._resource}"
        else:
            _LOGGER.warning("Keine IP Adresse vorhanden")

        _LOGGER.debug("HOST:%s", self._resource)

    def exract_data(self, soup: BeautifulSoup, label: str):
        """Extrahiert einen Wert aus dem HTML, basierend auf einem <b>-Label.

        Args:
            soup (BeautifulSoup): Das geparste HTML-Dokument.
            label (str): Der anzuzeigende HTML-Labeltext, z. B. "Messgerät IP:".

        Returns:
            str: Der extrahierte Wert als String.

        Raises:
            UpdateFailed: Wenn das Label im HTML nicht gefunden wurde.

        """
        label_tag = soup.find("b", string=label)

        if label_tag and label_tag.parent:
            full_text = label_tag.parent.get_text(strip=True)
            result_label = full_text.replace(label, "").strip()
        else:
            raise UpdateFailed(f"Label '{label}' nicht gefunden")

        return result_label

    async def _async_update_data(self):
        """Führt eine HTTP-Abfrage durch, parst HTML und extrahiert Sensordaten.

        Returns:
            dict: Schlüssel-Wert-Paare der extrahierten Sensordaten, z.B.
                  {"PowerMeterIp": "192.168.0.1", "MaximumPower": "8000 W", ...}

        Raises:
            UpdateFailed: Bei Netzwerkfehlern, Timeout oder fehlenden HTML-Elementen.

        """
        if self._resource:
            _LOGGER.debug("Abfrage - HOST: %s", self._resource)
            try:
                async with aiohttp.ClientSession() as session:
                    async with async_timeout.timeout(10):
                        async with session.get(self._resource) as response:
                            if response.status != 200:
                                raise UpdateFailed(
                                    f"Fehler beim Abruf: HTTP {response.status}"
                                )

                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            data = {}

                            for sensor in self._sensor_list:
                                key = sensor[0]  # z. B. "PowerMeterIp"
                                label = sensor[1]  # z. B. "Messgerät IP:"
                                value = self.exract_data(soup, label)
                                data[key] = value

                            return data

            except aiohttp.ClientError as e:
                raise UpdateFailed(f"Netzwerkfehler beim Abruf: {e}") from e

            except TimeoutError as e:
                raise UpdateFailed(
                    "Zeitüberschreitung beim Abrufen der HTML-Seite"
                ) from e

            except UpdateFailed:
                # Weiterreichen, da z. B. Label nicht gefunden wurde
                raise

            except Exception as e:
                _LOGGER.exception("Unerwarteter Fehler bei der Datenabfrage")
                raise UpdateFailed(f"Unerwarteter Fehler: {e}") from e
        else:
            return {}
