from datetime import timedelta

from custom_components.maxxi_charge_connect.const import DOMAIN

from homeassistant.components.integration.sensor import IntegrationSensor, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy

from .translationsForIntegrationSensors import get_localized_name


class PvTotalEnergy(IntegrationSensor):
    # _attr_entity_registry_enabled_default = False
    # _attr_translation_key = "PvTotalEnergy"
    # _attr_has_entity_name = True

    def __init__(self, hass, entry, source_entity_id: str):
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
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "mephdrac",
            "model": "CCU - Maxxicharge",
        }
