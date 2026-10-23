"""Oberklassen-Sensor für die Gesamtenergiezählung.

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte Energie über die Zeit aufsummiert.

Die Energiemenge wird mittels der Trapezregel integriert und in Kilowattstunden dargestellt.

Classes:
    TotalIntegralSensor: Oberklassen-Sensorentität zur Anzeige der aufsummierten Energie
"""

import logging
from decimal import Decimal
from datetime import timedelta

from homeassistant.components.integration.sensor import (
    IntegrationSensor,
    UnitOfTime,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant


from ..const import DEVICE_INFO, DOMAIN, CONF_CCU_VERSION, CCU_V1  # noqa: TID252
from ..tools import clean_title

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class TotalIntegralSensor(IntegrationSensor):
    """Sensorentität zur Anzeige der gesamten Energie (kWh).

    Diese Entität summiert Energie über die Zeit auf, um
    die Insgesamtenergie zu berechnen. Sie nutzt dafür die Trapezregel
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

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        source_entity_id: str,
    ) -> None:
        """Initialisiert den Sensor für die gesamte Energie."""

        super().__init__(
            integration_method="trapezoidal",
            name=None,
            round_digits=3,
            source_entity=source_entity_id,
            unique_id=(
                f"{entry.entry_id}_"
                f"{clean_title(self.__class__.__name__)}"
            ),
            device_class=SensorDeviceClass.ENERGY,
            unit_prefix="k",
            unit_time=UnitOfTime.HOURS,
            max_sub_interval=timedelta(seconds=120),
        )

        # IntegrationSensor setzt einen eigenen Namen.
        # Entfernen, damit Home Assistant unsere Übersetzung verwendet.
        del self._attr_name

        self.hass = hass
        self._entry = entry

        self._attr_translation_key = self.__class__.__name__
        self._attr_has_entity_name = True

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        self.my_icon = "mdi:counter"
        self._attr_icon = self.my_icon

        # Für Kompatibilität mit bestehender Logik
        self._unsub_time_reset = None

    def set_state_from_migration(self, value: Decimal):
        """Einen valid Status setzen, nach der Migration.

        Diese Methode dient dem Setzen eines Statusses nach einer erfolgreichen Migration
        von der YAML-Integration zu dieser. Sie sollte nicht aus anderen Gründen verwendet
        werden

        Args:
            value (Decimal): Statuswert, der als letzter Valid Status gezeigt werden soll.
        """

        _LOGGER.info("Setze neuen State: %s", value)
        self._state = value
        self._last_valid_state = value
        self.async_write_ha_state()

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

    @property
    def icon(self):
        """Liefert das Icon der Entity"""
        return self.my_icon

    @property
    def available(self) -> bool:
        """Der Energiesensor bleibt verfügbar, auch wenn der Quellsensor 'unavailable' ist.

        Er zeigt dann einfach den letzten gespeicherten Wert an.
        """

        return True

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
        ccu_version = self._entry.data.get(CONF_CCU_VERSION, CCU_V1)
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
            "model": f"CCU {ccu_version.upper()}",
        }
