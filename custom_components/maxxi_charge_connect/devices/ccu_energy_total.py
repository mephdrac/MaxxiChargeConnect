"""Sensor zur Gesamtenergieintegration der CCU.

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte Energie berechnet, die über einen Zeitraum verbraucht oder erzeugt wurde.
Die Integration erfolgt über eine trapezförmige Methode mit automatischer Einheitenskalierung.

Classes:
    CcuEnergyTotal: Sensorentität für die kumulierte Energieintegration der CCU.

"""

from datetime import timedelta

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from ..const import DEVICE_INFO, DOMAIN
from .translations_for_integration_sensors import clean_title, get_localized_name


class CcuEnergyTotal(IntegrationSensor):
    """Sensor für die kumulierte Energieintegration (z. B. einer CCU).

    Diese Entität summiert die Energie über die Zeit durch Integration
    der Leistungsmessung. Sie eignet sich zur Anzeige des Gesamtverbrauchs
    oder der Gesamteinspeisung.

    Attributes:
        _entry (ConfigEntry): Der Konfigurationseintrag dieser Entität.

    """

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Sensorentität für die Gesamtenergieintegration.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag dieser Integration.
            source_entity_id (str): Die Entity-ID der Quelle, die die Leistung liefert.

        """
        super().__init__(
            source_entity=source_entity_id,
            # name="CCU Energy Total",
            name=clean_title(entry.title)
            + "_"
            + get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_ccu_energy_total",
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
