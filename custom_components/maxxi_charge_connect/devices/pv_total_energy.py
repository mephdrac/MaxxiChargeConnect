"""Sensor zur PV-Gesamtproduktion in kWh.

Dieser Sensor summiert die PV-Produktion insgesamt.
"""

from datetime import timedelta

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from .translations_for_integration_sensors import get_localized_name


class PvTotalEnergy(IntegrationSensor):
    """Sensor zur Integration der PV-Produktionsleistung (kWh gesamt)."""

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert den täglichen PV-Energieproduktionssensor.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Die Konfigurationsinstanz der Integration.
            source_entity_id (str): Die Entity-ID der Quell-Leistungs-Sensorentität.

        """
        super().__init__(
            source_entity=source_entity_id,
            # name="PV Energy Total",
            name=get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_pv_energy_total",
            integration_method="trapezoidal",
            round_digits=3,
            unit_prefix="k",
            unit_time=UnitOfTime.HOURS,
            max_sub_interval=timedelta(seconds=120),
        )
        self._entry = entry
        self._attr_icon = "mdi:counter"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

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
