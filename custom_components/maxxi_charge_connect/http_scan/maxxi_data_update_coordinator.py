"""Coordinator-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert die Klasse MaxxiDataUpdateCoordinator, die regelmäßig
eine Web-Oberfläche per HTTP abruft, HTML parst und definierte Werte extrahiert,
um sie als Sensordaten in Home Assistant bereitzustellen.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import CONF_DEVICE_ID, HTTP_SCAN_EVENTNAME, NEIN, OPTIONAL, REQUIRED
from ..tools import fire_status_event

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # z.B. alle 30 Sekunden aktualisieren

CCU_V1_HTTP_SCAN_FIELDS = (
    ("PowerMeterIp", "Messgerät IP:", REQUIRED),
    ("PowerMeterType", "Messgerät Typ:", REQUIRED),
    ("MaximumPower", "Maximale Leistung:", REQUIRED),
    ("OfflineOutputPower", "Offline-Ausgangsleistung:", REQUIRED),
    ("NumberOfBatteries", "Batterien im System:", REQUIRED),
    ("OutputOffset", "Ausgabe korrigieren:", REQUIRED),
    ("CcuSpeed", "CCU-Geschwindigkeit:", REQUIRED),
    ("Microinverter", "Mikro-Wechselrichter-Typ:", REQUIRED),
    ("ResponseTolerance", "Reaktionstoleranz:", REQUIRED),
    ("MinimumBatteryDischarge", "Minimale Entladung der Batterie:", REQUIRED),
    ("MaximumBatteryCharge", "Maximale Akkuladung:", REQUIRED),
    ("DC/DC-Algorithmus", "DC/DC-Algorithmus:", REQUIRED),
    ("Cloudservice", "Cloudservice:", REQUIRED),
    ("LocalServer", "Lokalen Server nutzen:", NEIN),
    ("APIRoute", "API-Route:", OPTIONAL),
)


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
        self._device_id = entry.data[CONF_DEVICE_ID].strip()
        self._resource = (entry.data.get(CONF_IP_ADDRESS) or "").strip()

        if self._resource:
            if not self._resource.startswith(("http://", "https://")):
                self._resource = f"http://{self._resource}"
        else:
            _LOGGER.warning("Keine IP Adresse vorhanden")

        try:
            # The target is visible on the Status sensor. Exclude credentials, paths and queries.
            self.scan_target = urlsplit(self._resource).netloc.rpartition("@")[2]
        except ValueError:
            self.scan_target = ""

        self.scan_result = "Noch nicht abgefragt"
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
                    async with asyncio.timeout(10):
                        async with session.get(self._resource) as response:
                            if response.status != 200:
                                raise UpdateFailed(f"Fehler beim Abruf: HTTP {response.status}")

                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            data = {}
                            found_fields = 0
                            for key, label, mode in self._sensor_list:
                                try:
                                    data[key] = self.exract_data(soup, label)
                                except UpdateFailed:
                                    if mode == REQUIRED:
                                        _LOGGER.debug("HTTP-Scan %s: Feld %s fehlt", self._resource, label)
                                    else:
                                        data[key] = "Nein" if mode == NEIN else "nicht gesetzt"
                                else:
                                    found_fields += 1

                            if found_fields == 0:
                                raise UpdateFailed("Keine CCU-Felder in der HTTP-Antwort gefunden")

                            self.scan_result = f"{found_fields}/{len(self._sensor_list)} Felder gelesen"
                            json_data = {
                                "deviceId": str(self._device_id),
                                "ccu": str(self._device_id),
                                "ip_addr": str(self._resource),
                                "integration_state": "OK",
                                "message": "Http-Scan Sensoren ausgelesen.",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            await fire_status_event(self.hass, json_data, False, HTTP_SCAN_EVENTNAME)

                            return data

            except aiohttp.ClientError as e:
                self.scan_result = f"Netzwerkfehler ({type(e).__name__})"
                _LOGGER.error("HTTP-Scan %s: Netzwerkfehler beim Abruf: %s", self._resource, e)

                json_data = {
                    "deviceId": "Errors",
                    "ccu": str(self._device_id),
                    "ip_addr": str(self._resource),
                    "error": "Netzwerk",
                    "message": "Netzwerkfehler beim Abruf",
                    "exception": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await fire_status_event(self.hass, json_data, False, HTTP_SCAN_EVENTNAME)
                return {}

            except TimeoutError as e:
                self.scan_result = "Zeitüberschreitung"
                _LOGGER.error(
                    "%s: Zeitüberschreitung beim Abrufen von maxxi.local bzw. der IP (%s)",
                    e,
                    self._resource,
                )
                json_data = {
                    "deviceId": "Errors",
                    "ccu": str(self._device_id),
                    "ip_addr": str(self._resource),
                    "error": "Timeout",
                    "message": "Zeitüberschreitung beim Abrufen von maxxi.local bzw. der IP",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                await fire_status_event(self.hass, json_data, False, HTTP_SCAN_EVENTNAME)
                return {}

            except Exception as e:  # pylint: disable=broad-exception-caught
                self.scan_result = str(e) if isinstance(e, UpdateFailed) else "Unerwarteter Fehler beim HTTP-Scan"
                _LOGGER.error("HTTP-Scan %s: %s", self._resource, e)

                json_data = {
                    "deviceId": "Errors",
                    "ccu": str(self._device_id),
                    "ip_addr": str(self._resource),
                    "error": "Unerwartet",
                    "message": "Unerwarteter Fehler bei der Datenabfrage",
                    "exception": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await fire_status_event(self.hass, json_data, False, HTTP_SCAN_EVENTNAME)
                return {}
        else:
            self.scan_result = "Keine CCU-Adresse konfiguriert"
            json_data = {
                "deviceId": str(self._device_id),
                "ccu": str(self._device_id),
                "ip_addr": str(self._resource),
                "integration_state": "OK (ohne IP)",
                "message": "Es wurde keine IP eingeben, daher sind einige Sensoren auf unbekannt",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await fire_status_event(self.hass, json_data, False, HTTP_SCAN_EVENTNAME)
            return {}
