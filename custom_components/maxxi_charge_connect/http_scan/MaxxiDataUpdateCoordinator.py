# coordinator.py
import logging
from datetime import timedelta

import aiohttp
import async_timeout
from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # z.B. alle 30 Sekunden aktualisieren


class MaxxiDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="maxxi_charge_connect",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self._resource = entry.data["host"]
        if not self._resource.startswith(("http://", "https://")):
            self._resource = f"http://{self._resource}"

        _LOGGER.warning("HOST:" + self._resource)

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
                        label_text = "Messgerät IP:"
                        label = soup.find("b", string=label_text)
                        if label and label.parent:
                            full_text = label.parent.get_text(strip=True)
                            value = full_text.replace(label_text, "").strip()
                            return {"local_ip": value}
                        raise UpdateFailed(f"Label '{label_text}' nicht gefunden")
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen oder Parsen: {err}")
