# coordinator.py
import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.const import CONF_IP_ADDRESS
from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # z.B. alle 30 Sekunden aktualisieren


class MaxxiDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, sensorList):
        super().__init__(
            hass,
            _LOGGER,
            name="maxxi_charge_connect",
            update_interval=SCAN_INTERVAL,
        )

        self._sensorList = sensorList
        self.entry = entry
        self._resource = entry.data[CONF_IP_ADDRESS]
        if not self._resource.startswith(("http://", "https://")):
            self._resource = f"http://{self._resource}"

        _LOGGER.warning("HOST:" + self._resource)

    def exract_data(self, soup: BeautifulSoup, label: str):
        # Daten aus HTML extrahieren
        label_tag = soup.find("b", string=label)

        if label_tag and label_tag.parent:
            full_text = label_tag.parent.get_text(strip=True)
            result_label = full_text.replace(label, "").strip()
        else:
            raise UpdateFailed(f"Label '{label}' nicht gefunden")

        return result_label

    async def _async_update_data(self):
        """API abfragen und Daten zurückgeben"""
        _LOGGER.warning("Abfrage - HOST: " + self._resource)
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

                        for sensor in self._sensorList:
                            key = sensor[0]  # z. B. "PowerMeterIp"
                            label = sensor[1]  # z. B. "Messgerät IP:"
                            value = self.exract_data(soup, label)
                            data[key] = value

                        return data

                        # for element in self._sensorList:
                        #     power_meter_ip = self.exract_data(soup, element[1])

                        # power_meter_ip = self.exract_data(soup, "Messgerät IP:")
                        # power_meter_typ = self.exract_data(soup, "Messgerät Typ:")
                        # maximumPower = self.exract_data(soup, "Maximale Leistung:")
                        # offlineOutputPower = self.exract_data(
                        #     soup, "Offline-Ausgangsleistung:"
                        # )
                        # numberOfBatteries = self.exract_data(
                        #     soup, "Batterien im System:"
                        # )
                        # outputOffset = self.exract_data(soup, "Ausgabe korrigieren:")

                        # return {
                        #     "PowerMeterIp": power_meter_ip,
                        #     "PowerMeterType": power_meter_typ,
                        #     "MaximumPower": maximumPower,
                        #     "OfflineOutputPower": offlineOutputPower,
                        #     "NumberOfBatteries": numberOfBatteries,
                        #     "OutputOffset": outputOffset,
                        # }

        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen oder Parsen: {err}")
