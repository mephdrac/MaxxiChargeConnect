"""Tests für das UptimeSensor-Modul der MaxxiChargeConnect-Integration.

Dieses Testmodul prüft die Uptime-Berechnung und die
Fehlerbehandlung des UptimeSensor.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, UTC, timedelta

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.uptime_sensor import UptimeSensor

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def sensor():
    """Gibt ein Mock-Konfigurationsobjekt für den Sensor zurück."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": "abc123"}

    sensor_obj = UptimeSensor(entry)
    sensor_obj.hass = MagicMock()
    sensor_obj.async_write_ha_state = MagicMock()

    return sensor_obj


@pytest.mark.asyncio
async def test_uptime_sensor_initialization(sensor):
    """Testet die Initialisierung des UptimeSensor."""
    assert sensor._attr_unique_id == "test_entry_id_uptime_sensor"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:timer-outline"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.TIMESTAMP  # pylint: disable=protected-access
    assert sensor._last_state_update is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_uptime_sensor_first_update(sensor):
    """Testet das erste empfangene Uptime."""
    test_uptime_ms = 86400000  # 1 Tag in Millisekunden
    
    await sensor.handle_update({"uptime": test_uptime_ms})
    
    # Sollte Startzeit berechnen
    expected_start = datetime.now(tz=UTC) - timedelta(milliseconds=test_uptime_ms)
    assert sensor._attr_native_value is not None  # pylint: disable=protected-access
    assert sensor._last_state_update is not None  # pylint: disable=protected-access
    
    # Extra Attribute prüfen
    attrs = sensor._attr_extra_state_attributes  # pylint: disable=protected-access
    assert attrs["uptime"] == "1d 0h 0m 0s"
    assert attrs["raw_ms"] == test_uptime_ms


@pytest.mark.asyncio
async def test_uptime_sensor_format_calculation(sensor):
    """Testet die Uptime-Formatberechnung."""
    # Test: 2 Tage, 3 Stunden, 45 Minuten, 30 Sekunden
    test_uptime_ms = (2 * 86400 + 3 * 3600 + 45 * 60 + 30) * 1000
    
    await sensor.handle_update({"uptime": test_uptime_ms})
    
    attrs = sensor._attr_extra_state_attributes  # pylint: disable=protected-access
    assert attrs["uptime"] == "2d 3h 45m 30s"
    assert attrs["raw_ms"] == test_uptime_ms


@pytest.mark.asyncio
async def test_uptime_sensor_daily_update_only(sensor):
    """Testet, dass der State nur einmal pro Tag aktualisiert wird."""
    test_uptime_ms = 3600000  # 1 Stunde
    
    # Erste Aktualisierung
    await sensor.handle_update({"uptime": test_uptime_ms})
    first_state = sensor._attr_native_value  # pylint: disable=protected-access
    
    # Zweite Aktualisierung kurz danach (sollte State nicht ändern)
    await sensor.handle_update({"uptime": test_uptime_ms + 60000})  # +1 Minute
    second_state = sensor._attr_native_value  # pylint: disable=protected-access
    
    # State sollte gleich bleiben (tägliche Aktualisierung)
    assert first_state == second_state
    
    # Aber raw_ms sollte sich aktualisieren
    attrs = sensor._attr_extra_state_attributes  # pylint: disable=protected-access
    assert attrs["raw_ms"] == test_uptime_ms + 60000


@pytest.mark.asyncio
async def test_uptime_sensor_missing_field(sensor):
    """Testet Verhalten bei fehlendem uptime-Feld."""
    await sensor.handle_update({})
    
    # Sollte nichts ändern
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._last_state_update is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_uptime_sensor_none_value(sensor):
    """Testet Verhalten bei uptime = None."""
    await sensor.handle_update({"uptime": None})
    
    # Sollte nichts ändern
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_uptime_sensor_string_value(sensor):
    """Testet Konvertierung von String zu int."""
    await sensor.handle_update({"uptime": "86400000"})  # 1 Tag als String
    
    assert sensor._attr_native_value is not None  # pylint: disable=protected-access
    attrs = sensor._attr_extra_state_attributes  # pylint: disable=protected-access
    assert attrs["uptime"] == "1d 0h 0m 0s"
    assert attrs["raw_ms"] == 86400000


@pytest.mark.asyncio
async def test_uptime_sensor_invalid_string(sensor):
    """Testet Verhalten bei ungültigem String."""
    await sensor.handle_update({"uptime": "invalid"})
    
    # Sollte nichts ändern
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_uptime_sensor_negative_value(sensor):
    """Testet Verhalten bei negativem Uptime-Wert."""
    await sensor.handle_update({"uptime": -1000})
    
    # Sollte nichts ändern
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_uptime_sensor_zero_value(sensor):
    """Testet Verhalten bei Uptime = 0."""
    await sensor.handle_update({"uptime": 0})
    
    assert sensor._attr_native_value is not None  # pylint: disable=protected-access
    attrs = sensor._attr_extra_state_attributes  # pylint: disable=protected-access
    assert attrs["uptime"] == "0d 0h 0m 0s"
    assert attrs["raw_ms"] == 0


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
