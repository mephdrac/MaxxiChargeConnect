"""Sensor zur Anzeige der täglichen Energieerfassung der CCU.

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die täglich verbrauchte Energie einer Quelle über den Tag aufsummiert. Der Zähler wird
jeden Tag um Mitternacht zurückgesetzt.

Classes:
    CcuEnergyToday: Sensorentität für die tägliche Energieintegration mit täglichem Reset.
"""

from datetime import timedelta
import logging

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from .translations_for_integration_sensors import get_localized_name

_LOGGER = logging.getLogger(__name__)


class CcuEnergyToday(IntegrationSensor):
    """Sensor für die tägliche Energieintegration (z.B. durch eine CCU).

    Diese Entität berechnet den täglichen Energieverbrauch, indem sie die Leistung
    über die Zeit integriert. Um Mitternacht wird der Zähler automatisch zurückgesetzt.

    Attributes:
        _entry (ConfigEntry): Der Konfigurationseintrag für diese Entität.
        _last_reset (datetime): Zeitpunkt des letzten täglichen Resets in UTC.
        _unsub_time_reset (Callable | None): Callback zum Abmelden des täglichen Resets.

    """

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Sensorentität für den täglichen Energieverbrauch.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag dieser Integration.
            source_entity_id (str): Die Entity-ID der Quelle, die die Leistung liefert.

        """
        super().__init__(
            source_entity=source_entity_id,
            # name="CCU Energy Today",
            name=get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_CcuEnergyToday",
            integration_method="trapezoidal",
            round_digits=3,
            unit_prefix="k",
            unit_time=UnitOfTime.HOURS,
            max_sub_interval=timedelta(seconds=120),
        )
        self._unsub_time_reset = None
        self._entry = entry
        self._attr_icon = "mdi:counter"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

        # Setze initialen Reset-Zeitpunkt auf heutige Mitternacht lokal
        local_midnight = dt_util.start_of_local_day()
        self._last_reset = dt_util.as_utc(local_midnight)

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wurde.

        Registriert einen täglichen Reset der integrierten Energie um 0:00 Uhr lokaler Zeit.
        """
        await super().async_added_to_hass()

        # Registriere täglichen Reset um 0:00 Uhr lokale Zeit
        self._unsub_time_reset = async_track_time_change(
            self.hass,
            self._reset_energy_daily,
            hour=0,
            minute=0,
            second=0,
        )

        if self._unsub_time_reset is not None:
            self.async_on_remove(self._unsub_time_reset)

    async def _reset_energy_daily(self, now):
        """Setzt den Tageszähler um Mitternacht zurück.

        Args:
            now (datetime): Der aktuelle Zeitpunkt (wird von Home Assistant übergeben).

        """
        _LOGGER.info("Resetting daily energy at %s", now)

        # Setze Reset-Zeitpunkt auf aktuelle Mitternacht lokal (als UTC)
        local_midnight = dt_util.start_of_local_day()
        self._last_reset = dt_util.as_utc(local_midnight)

        self.async_write_ha_state()

    @property
    def last_reset(self):
        """Gibt den letzten Zeitpunkt zurück, zu dem die Tagesenergie zurückgesetzt wurde.

        Returns:
            datetime: Zeitpunkt des letzten Resets in UTC.

        """
        return self._last_reset

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
