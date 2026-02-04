"""Tests für die CCUTemperaturSensor Entity im MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature, EntityCategory
import pytest

from custom_components.maxxi_charge_connect.devices.ccu_temperatur_sensor import (
    CCUTemperaturSensor,
)


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__init():
    """Initialisierung der CCUTemperaturSensor Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = CCUTemperaturSensor(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._attr_entity_registry_enabled_default is False  # pylint: disable=protected-access
    assert sensor._attr_translation_key == "CCUTemperaturSensor"  # pylint: disable=protected-access
    assert sensor._attr_has_entity_name is True  # pylint: disable=protected-access
    assert sensor._attr_unique_id == "1234abcd_ccu_temperatur_sensor"  # pylint: disable=protected-access
    assert sensor.icon == "mdi:temperature-celsius"
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__device_info():
    """Testet die device_info Eigenschaft der CCUTemperaturSensor Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = CCUTemperaturSensor(dummy_config_entry)

    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_alles_ok():
    """handle_update Methode der CCUTemperaturSensor Entity testen, wenn alles ok ist."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": [
            {
                "ccuTemperature": 25.5
            },
            {
                "ccuTemperature": 26.0
            },
            {
                "ccuTemperature": 24.5
            }
        ]
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 25.3  # pylint: disable=protected-access (gerundet)


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_keine_daten():
    """Testet handle_update mit fehlenden Daten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {}  # Keine convertersInfo

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_leere_converters():
    """Testet handle_update mit leerer convertersInfo."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": []
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_fehlende_temperatur():
    """Testet handle_update mit fehlender ccuTemperature."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": [
            {
                "otherField": "value"
            },
            {
                "ccuTemperature": 25.0
            }
        ]
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 25.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_ungültige_werte():
    """Testet handle_update mit ungültigen Temperaturwerten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = CCUTemperaturSensor(dummy_config_entry)

    # Test mit zu niedriger Temperatur
    data = {
        "convertersInfo": [
            {
                "ccuTemperature": -50  # Unter -40°C
            },
            {
                "ccuTemperature": 25.0
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 25.0  # pylint: disable=protected-access

    # Test mit zu hoher Temperatur
    data = {
        "convertersInfo": [
            {
                "ccuTemperature": 90  # Über 85°C
            },
            {
                "ccuTemperature": 25.0
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 25.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_string_konvertierung():
    """Testet handle_update mit String-Konvertierung."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": [
            {
                "ccuTemperature": "25.5"
            },
            {
                "ccuTemperature": "26.0"
            }
        ]
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 25.8  # pylint: disable=protected-access (gerundet)


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_ungültiger_string():
    """Testet handle_update mit ungültigem String."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": [
            {
                "ccuTemperature": "invalid"
            },
            {
                "ccuTemperature": 25.0
            }
        ]
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 25.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_ungültige_datenstruktur():
    """Testet handle_update mit ungültiger Datenstruktur."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = CCUTemperaturSensor(dummy_config_entry)

    # Test mit nicht-Dictionary Converter
    data = {
        "convertersInfo": [
            "invalid_converter",
            {
                "ccuTemperature": 25.0
            }
        ]
    }

    await sensor.handle_update(data)

    assert sensor._attr_native_value == 25.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_grenzwerte():
    """Testet handle_update mit Grenzwerten."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = CCUTemperaturSensor(dummy_config_entry)

    # Test mit unterem Grenzwert (-40°C)
    data = {
        "convertersInfo": [
            {
                "ccuTemperature": -40
            },
            {
                "ccuTemperature": 20.0
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == -10.0  # pylint: disable=protected-access (gerundet)

    # Test mit oberem Grenzwert (85°C)
    data = {
        "convertersInfo": [
            {
                "ccuTemperature": 85
            },
            {
                "ccuTemperature": 20.0
            }
        ]
    }

    await sensor.handle_update(data)
    assert sensor._attr_native_value == 52.5  # pylint: disable=protected-access (gerundet)


@pytest.mark.asyncio
async def test_ccu_temperatur_sensor__handle_update_keine_gültige_temperaturen():
    """Testet handle_update wenn keine gültigen Temperaturen gefunden werden."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "convertersInfo": [
            {
                "ccuTemperature": -50  # Ungültig
            },
            {
                "ccuTemperature": 90   # Ungültig
            }
        ]
    }

    sensor = CCUTemperaturSensor(dummy_config_entry)

    await sensor.handle_update(data)

    assert sensor._attr_native_value is None  # pylint: disable=protected-access
