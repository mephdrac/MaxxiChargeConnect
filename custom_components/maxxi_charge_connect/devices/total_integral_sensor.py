from datetime import UTC, datetime, timedelta
import logging

from homeassistant.components.integration.sensor import (
    UNIT_PREFIXES,
    UNIT_TIME,
    IntegrationSensor,
    UnitOfTime,
    _IntegrationMethod,
    _IntegrationTrigger,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from ..tools import clean_title

_LOGGER = logging.getLogger(__name__)


class TotalIntegralSensor(IntegrationSensor):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        self._attr_translation_key = self.__class__.__name__
        self._attr_unique_id = (
            f"{entry.entry_id}_{clean_title(self.__class__.__name__)}"
        )
        self._source_entity = source_entity_id
        self._sensor_source_id = source_entity_id
        self._round_digits = 3
        self._state = None
        self._integration_method = self._method = _IntegrationMethod.from_name(
            "trapezoidal"
        )

        # self._attr_name = name if name is not None else f"{source_entity} integral"
        self._unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self.unit_prefix = "k"
        self._unit_prefix_string = "" if self.unit_prefix is None else self.unit_prefix
        self._unit_of_measurement: str | None = None
        self._unit_prefix = UNIT_PREFIXES[self.unit_prefix]
        self.unit_time = UnitOfTime.HOURS
        self._unit_time = UNIT_TIME[self.unit_time]
        self._unit_time_str = self.unit_time
        self._last_valid_state = None
        # self._attr_device_info = device_info
        self._max_sub_interval = timedelta(seconds=120)
        self._last_integration_time = datetime.now(tz=UTC)
        self._last_integration_trigger = _IntegrationTrigger.StateEvent
        self._attr_suggested_display_precision = self._round_digits or 2
        # Zuweisung
        self._max_sub_interval_exceeded_callback = (
            self._handle_max_sub_interval_exceeded
        )

        # Setzte neue Attribute
        self._entry = entry
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self.my_icon = "mdi:counter"
        self._attr_icon = self.my_icon

        # Setze initialen Reset-Zeitpunkt auf heutige Mitternacht lokal
        self._unsub_time_reset = None
        local_midnight = dt_util.start_of_local_day()
        self._last_reset = dt_util.as_utc(local_midnight)

    def _handle_max_sub_interval_exceeded(self):
        _LOGGER.debug(
            "[%s] Kein neuer Wert innerhalb von %s empfangen – Integration pausiert",
            self.entity_id,
            self._max_sub_interval,
        )
        # self._state = None
        # self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wird.

        Registriert einen täglichen Reset der Energiewerte um 0:00 Uhr lokale Zeit.
        """
        await super().async_added_to_hass()

        if self._unsub_time_reset is not None:
            self.async_on_remove(self._unsub_time_reset)

    @property
    def icon(self):
        return self.my_icon

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
