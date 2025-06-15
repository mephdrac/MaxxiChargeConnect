"""Sensor für die gesamte Batterieentladeenergie (BatteryTotalEnergyDischarge).

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte aus der Batterie entnommene Energie über die Zeit aufsummiert.

Die Energiemenge wird mittels der Trapezregel aus der Entladeleistung (Watt) integriert
und in Kilowattstunden dargestellt.

Classes:
    BatteryTotalEnergyDischarge: Sensorentität zur Anzeige der aufsummierten Batterieentladeenergie.
"""

from datetime import timedelta

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from ..const import DEVICE_INFO, DOMAIN  # noqa: TID252
from .translations_for_integration_sensors import clean_title, get_localized_name


class BatteryTotalEnergyDischarge(IntegrationSensor):
    """Sensorentität zur Anzeige der gesamten Batterieentladeenergie (kWh).

    Diese Entität summiert die Entladeleistung der Batterie über die Zeit auf, um
    die insgesamt abgegebene Energie zu berechnen. Sie nutzt dafür die Trapezregel
    zur Integration und stellt den Wert in Kilowattstunden dar.

    Attributes:
        _attr_entity_registry_enabled_default (bool): Gibt an, ob die Entität standardmäßig
           aktiviert ist.
        _entry (ConfigEntry): Die Konfigurationsdaten dieser Entität.
        _attr_icon (str): Das Symbol, das in der Benutzeroberfläche angezeigt wird.
        _attr_device_class (str): Gibt den Typ des Sensors an (hier: ENERGY).
        _attr_state_class (str): Gibt die Art des Sensorzustands an (TOTAL_INCREASING).
        _attr_native_unit_of_measurement (str): Die verwendete Energieeinheit (kWh).

    """

    _attr_entity_registry_enabled_default = True

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Sensorentität für die Batterieentladeenergie.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Der Konfigurationseintrag mit den Einstellungen dieser Entität.
            source_entity_id (str): Die Quell-Entity-ID, die die Entladeleistung in Watt liefert.

        """
        super().__init__(
            source_entity=source_entity_id,
            # name="Battery Discharge Total",
            name=clean_title(entry.title)
            + "_"
            + get_localized_name(hass, self.__class__.__name__),
            unique_id=f"{entry.entry_id}_battery_energy_total_discharge",
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
