from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.maxxi_charge_connect.devices.pv_self_consumption_energy_total import (
    PvSelfConsumptionEnergyTotal,
)

@pytest.mark.asyncio
async def test_pv_self_consumption_energy_total_init(caplog):
        
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    dummy_config_entry.data = {}
    dummy_config_entry.options = {}

    source_entity = "sensor.test_power"
    sensor = PvSelfConsumptionEnergyTotal(hass, dummy_config_entry, source_entity)

    # Grundlegende Attribute prüfen
    assert sensor._source_entity == source_entity
    assert sensor._attr_device_class == "energy"
    assert sensor._attr_native_unit_of_measurement == "kWh"
    assert sensor.icon == "mdi:counter"
    assert sensor._attr_unique_id == "1234abcd_pvselfconsumptionenergytotal"

    # 👉 Patch den super()-Call zur Elternmethode
    with patch("custom_components.maxxi_charge_connect.devices.total_integral_sensor.TotalIntegralSensor.async_added_to_hass"):
        await sensor.async_added_to_hass()

    
    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title