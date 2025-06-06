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

                        # Erster Wert: PowerMeterIP
                        label_ip = "Messgerät IP:"
                        label_ip_tag = soup.find("b", string=label_ip)
                        if label_ip_tag and label_ip_tag.parent:
                            full_text_ip = label_ip_tag.parent.get_text(strip=True)
                            power_meter_ip = full_text_ip.replace(label_ip, "").strip()
                        else:
                            raise UpdateFailed(f"Label '{label_ip}' nicht gefunden")

                        # Zweiter Wert: PowerMeterTyp (Beispiel-Label)
                        label_typ = "Messgerät Typ:"
                        label_typ_tag = soup.find("b", string=label_typ)
                        if label_typ_tag and label_typ_tag.parent:
                            full_text_typ = label_typ_tag.parent.get_text(strip=True)
                            power_meter_typ = full_text_typ.replace(
                                label_typ, ""
                            ).strip()
                        else:
                            raise UpdateFailed(f"Label '{label_typ}' nicht gefunden")

                        # MaximumPower
                        label_typ = "Maximale Leistung:"
                        label_typ_tag = soup.find("b", string=label_typ)
                        if label_typ_tag and label_typ_tag.parent:
                            full_text_typ = label_typ_tag.parent.get_text(strip=True)
                            maximumPower = full_text_typ.replace(label_typ, "").strip()
                        else:
                            raise UpdateFailed(f"Label '{label_typ}' nicht gefunden")

                        # OfflineOutputPower
                        label_typ = "Offline-Ausgangsleistung:"
                        label_typ_tag = soup.find("b", string=label_typ)
                        if label_typ_tag and label_typ_tag.parent:
                            full_text_typ = label_typ_tag.parent.get_text(strip=True)
                            offlineOutputPower = full_text_typ.replace(
                                label_typ, ""
                            ).strip()
                        else:
                            raise UpdateFailed(f"Label '{label_typ}' nicht gefunden")

                        # NumberOfBatteries
                        label_typ = "Batterien im System:"
                        label_typ_tag = soup.find("b", string=label_typ)
                        if label_typ_tag and label_typ_tag.parent:
                            full_text_typ = label_typ_tag.parent.get_text(strip=True)
                            numberOfBatteries = full_text_typ.replace(
                                label_typ, ""
                            ).strip()
                        else:
                            raise UpdateFailed(f"Label '{label_typ}' nicht gefunden")

                        # Beide Werte zurückgeben
                        return {
                            "PowerMeterIp": power_meter_ip,
                            "PowerMeterType": power_meter_typ,
                            "MaximumPower": maximumPower,
                            "OfflineOutputPower": offlineOutputPower,
                            "NumberOfBatteries": numberOfBatteries,
                        }

        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen oder Parsen: {err}")
