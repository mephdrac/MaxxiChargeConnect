"""Tests für die GridImportEnergyTotal Entity."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.maxxi_charge_connect.devices.grid_import_energy_total import (
    GridImportEnergyTotal,
)


@pytest.mark.asyncio
async def test_grid_export_total_init():
    """Testet die Initialisierung der GridImportEnergyTotal Entity."""

    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"
    dummy_config_entry.data = {}
    dummy_config_entry.options = {}

    source_entity = "sensor.test_power"
    sensor = GridImportEnergyTotal(hass, dummy_config_entry, source_entity)

    # Grundlegende Attribute prüfen
    assert sensor._source_entity == source_entity  # pylint: disable=protected-access
    assert sensor._attr_device_class == "energy"  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == "kWh"  # pylint: disable=protected-access
    assert sensor.icon == "mdi:counter"
    assert sensor._attr_unique_id == "1234abcd_gridimportenergytotal"  # pylint: disable=protected-access

    # 👉 Patch den super()-Call zur Elternmethode
    with patch("custom_components.maxxi_charge_connect.devices.total_integral_sensor.TotalIntegralSensor.async_added_to_hass"):
        await sensor.async_added_to_hass()

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title
